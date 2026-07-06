"""Mutation quality scoring (Prompt 154)."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationRecord, get_mutation_store

logger = logging.getLogger(__name__)

_OUTCOME_SCORES = {
    "success": 1.0,
    "failure": 0.0,
    "partial": 0.5,
}


@dataclass
class QualitySample:
    mutation_id: str
    task_id: str | None
    run_id: str | None
    outcome: str
    score: float
    feedback: str | None
    sampled_at: datetime


class QualityScorer:
    """Update mutation quality scores from observed production outcomes."""

    ALPHA = 0.3
    AUTO_QUARANTINE_THRESHOLD = 0.3
    AUTO_PROMOTE_THRESHOLD = 0.85
    AUTO_PROMOTE_MIN_USES = 5

    def __init__(self, store=None) -> None:
        self._store = store or get_mutation_store()

    def record_sample(
        self,
        mutation_id: str,
        outcome: str,
        run_id: str | None = None,
        task_id: str | None = None,
        feedback: str | None = None,
    ) -> float:
        sample_score = _OUTCOME_SCORES.get(outcome, 0.5)
        record = self._store.get_generated_tool(mutation_id)
        if record is None:
            return sample_score

        self._store.insert_quality_sample(
            mutation_id=mutation_id,
            outcome=outcome,
            score=sample_score,
            run_id=run_id,
            task_id=task_id,
            feedback=feedback,
        )

        old_score = record.quality_score
        if old_score is None:
            new_score = sample_score
        else:
            new_score = self.ALPHA * sample_score + (1.0 - self.ALPHA) * old_score

        use_count = record.use_count + 1
        metadata = dict(record.metadata)
        updated = self._store.update_mutation_usage(
            mutation_id,
            quality_score=new_score,
            use_count=use_count,
            metadata=metadata,
        )
        if updated is None:
            return new_score

        self._check_auto_quarantine(updated, new_score)
        self._check_auto_promote(updated, new_score, use_count)
        return new_score

    def record_tool_use(
        self,
        tool_name: str,
        run_id: str,
        success: bool,
        error: str | None = None,
        *,
        workspace_id: str = "default",
    ) -> None:
        settings = get_mutation_settings()
        if not settings.enabled:
            return
        record = self._store.find_approved_mutation_by_name(workspace_id, tool_name, tier="tool")
        if record is None:
            return
        outcome = "success" if success else "failure"
        self.record_sample(
            record.id,
            outcome,
            run_id=run_id,
            feedback=error,
        )

    def record_prompt_use(
        self,
        workspace_id: str,
        prompt_key: str,
        run_id: str,
        outcome: str,
    ) -> None:
        settings = get_mutation_settings()
        if not settings.enabled:
            return
        record = self._store.find_active_prompt_mutation(workspace_id, prompt_key)
        if record is None:
            return
        self.record_sample(record.id, outcome, run_id=run_id)

    def get_quality_history(self, mutation_id: str, limit: int = 50) -> list[QualitySample]:
        rows = self._store.get_quality_samples(mutation_id, limit=limit)
        samples: list[QualitySample] = []
        for row in rows:
            sampled_at = row.get("sampled_at")
            if not isinstance(sampled_at, datetime):
                sampled_at = datetime.fromisoformat(str(sampled_at))
            samples.append(
                QualitySample(
                    mutation_id=mutation_id,
                    task_id=row.get("task_id"),
                    run_id=row.get("run_id"),
                    outcome=str(row.get("outcome") or "partial"),
                    score=float(row.get("score") or 0.0),
                    feedback=row.get("feedback"),
                    sampled_at=sampled_at,
                )
            )
        return samples

    def _check_auto_quarantine(self, record: MutationRecord, score: float) -> None:
        if score >= self.AUTO_QUARANTINE_THRESHOLD:
            return
        if record.status == "quarantined":
            return

        if record.tier == "tool":
            self._store.quarantine_tool_mutation(record)
        elif record.tier == "prompt":
            try:
                from keprix.mutation.prompt_store import get_prompt_store

                get_prompt_store().rollback_to_previous(
                    record.workspace_id,
                    record.name,
                    rolled_back_by="quality_scorer",
                )
            except Exception as exc:
                logger.warning("prompt rollback during quarantine failed: %s", exc)
            metadata = dict(record.metadata)
            metadata["quarantined"] = True
            self._store._set_status_and_metadata(record.id, "quarantined", metadata)
        elif record.tier == "code":
            metadata = dict(record.metadata)
            metadata["quarantined"] = True
            self._store._set_status_and_metadata(record.id, "quarantined", metadata)

        _notify_operator(
            record.workspace_id,
            title=f"Mutation quarantined: {record.name}",
            message=(
                f"Mutation {record.name} ({record.tier}) was auto-quarantined "
                f"after quality score dropped to {score:.2f}."
            ),
            source_id=record.id,
        )

    def _check_auto_promote(self, record: MutationRecord, score: float, use_count: int) -> None:
        if score <= self.AUTO_PROMOTE_THRESHOLD or use_count < self.AUTO_PROMOTE_MIN_USES:
            return
        if record.metadata.get("promoted"):
            return
        metadata = dict(record.metadata)
        metadata["promoted"] = True
        self._store.update_mutation_usage(
            record.id,
            quality_score=score,
            use_count=use_count,
            metadata=metadata,
        )


_scorer: QualityScorer | None = None


def get_quality_scorer() -> QualityScorer:
    global _scorer
    if _scorer is None:
        _scorer = QualityScorer()
    return _scorer


_FAILURE_CATEGORIES = frozenset(
    {"repeated_failure", "tool_failure", "low_eval", "user_correction"}
)


def classify_run_outcome(record, proposals) -> str:
    """Classify a completed run as success, partial, or failure."""
    if not proposals:
        return "success" if record.ok else "failure"
    failure_count = sum(1 for proposal in proposals if proposal.category in _FAILURE_CATEGORIES)
    if failure_count == 0:
        return "success"
    if failure_count > len(proposals) / 2:
        return "failure"
    return "partial"


def _tool_result_has_error(result: Any) -> tuple[bool, str | None]:
    if isinstance(result, dict):
        error = result.get("error")
        return bool(error), str(error) if error else None
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                error = parsed.get("error")
                return bool(error), str(error) if error else None
        except json.JSONDecodeError:
            pass
    return False, None


def maybe_record_generated_tool_use(
    tool_name: str,
    run_id: str | None,
    result: Any,
    *,
    workspace_id: str = "default",
) -> None:
    """Record quality sample when a generated tool completes."""
    try:
        from tools.registry import registry

        if registry.get_toolset_for_tool(tool_name) != "generated":
            return
        has_error, error = _tool_result_has_error(result)
        get_quality_scorer().record_tool_use(
            tool_name=tool_name,
            run_id=run_id or "unknown",
            success=not has_error,
            error=error,
            workspace_id=workspace_id,
        )
    except Exception as exc:
        logger.debug("mutation quality tool hook failed: %s", exc)


def _notify_operator(
    workspace_id: str,
    *,
    title: str,
    message: str,
    source_id: str | None = None,
) -> None:
    try:
        from keprix.backend.notifications.inbox import get_inbox_service

        async def _send() -> None:
            await get_inbox_service().send_notification(
                workspace_id,
                "governance_policy_alert",
                severity="warning",
                title=title,
                message=message,
                source="mutation_quality",
                source_id=source_id,
            )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_send())
        except RuntimeError:
            asyncio.run(_send())
    except Exception as exc:
        logger.warning("mutation quarantine notification failed: %s", exc)
