"""Mutation pruning (Prompt 154)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationRecord, get_mutation_store

logger = logging.getLogger(__name__)

_STALE_STAGED_DAYS = 30
_ROLLED_BACK_RETENTION_DAYS = 90


@dataclass
class PruneReport:
    pruned_tools: list[str] = field(default_factory=list)
    pruned_prompts: list[str] = field(default_factory=list)
    pruned_code: list[str] = field(default_factory=list)
    total_pruned: int = 0
    space_reclaimed_bytes: int = 0


class MutationPruner:
    """Prune low-value mutations to keep the mutation store healthy."""

    def __init__(self, store=None) -> None:
        self._store = store or get_mutation_store()
        self._settings = get_mutation_settings()

    def prune_unused_tools(self, dry_run: bool = False, *, workspace_id: str = "default") -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._settings.prune_after_days)
        pruned: list[str] = []
        for record in self._all_records(workspace_id, tier="tool", status="approved"):
            if not self._is_unused_low_score(record, cutoff):
                continue
            if not dry_run:
                self._prune_tool_record(record)
            pruned.append(record.name)
        return pruned

    def prune_stale_staged(self, dry_run: bool = False, *, workspace_id: str = "default") -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_STAGED_DAYS)
        expired: list[str] = []
        for record in self._all_records(workspace_id, status="staged"):
            if record.recorded_at >= cutoff:
                continue
            if not dry_run:
                metadata = dict(record.metadata)
                metadata["expired_reason"] = "stale_staged"
                self._store._set_status_and_metadata(record.id, "expired", metadata)
            expired.append(record.id)
        return expired

    def prune_excess_tools(self, dry_run: bool = False, *, workspace_id: str = "default") -> list[str]:
        approved = self._all_records(workspace_id, tier="tool", status="approved")
        limit = self._settings.max_generated_tools
        if len(approved) <= limit:
            return []
        ranked = sorted(
            approved,
            key=lambda row: (
                row.quality_score if row.quality_score is not None else 0.0,
                row.use_count,
            ),
        )
        excess = len(approved) - limit
        pruned: list[str] = []
        for record in ranked[:excess]:
            if not dry_run:
                self._prune_tool_record(record)
            pruned.append(record.name)
        return pruned

    def run_full_prune(self, dry_run: bool = False, *, workspace_id: str = "default") -> PruneReport:
        report = PruneReport()
        report.pruned_tools.extend(self.prune_unused_tools(dry_run=dry_run, workspace_id=workspace_id))
        report.pruned_tools.extend(self.prune_excess_tools(dry_run=dry_run, workspace_id=workspace_id))

        stale_ids = self.prune_stale_staged(dry_run=dry_run, workspace_id=workspace_id)
        for mutation_id in stale_ids:
            record = self._store.get_generated_tool(mutation_id)
            if record is None:
                continue
            if record.tier == "prompt":
                report.pruned_prompts.append(record.name)
            elif record.tier == "code":
                report.pruned_code.append(record.name)

        rolled_back_bytes = self._prune_rolled_back_source(dry_run=dry_run, workspace_id=workspace_id)
        report.space_reclaimed_bytes += rolled_back_bytes
        report.total_pruned = (
            len(report.pruned_tools) + len(report.pruned_prompts) + len(report.pruned_code)
        )
        logger.info(
            "mutation prune complete dry_run=%s tools=%d prompts=%d code=%d bytes=%d",
            dry_run,
            len(report.pruned_tools),
            len(report.pruned_prompts),
            len(report.pruned_code),
            report.space_reclaimed_bytes,
        )
        return report

    def _all_records(
        self,
        workspace_id: str,
        *,
        tier: str | None = None,
        status: str | None = None,
    ) -> list[MutationRecord]:
        items, _total = self._store.list_mutations(
            workspace_id,
            tier=tier,
            status=status,
            page=1,
            per_page=10_000,
        )
        return items

    def _is_unused_low_score(self, record: MutationRecord, cutoff: datetime) -> bool:
        if record.quality_score is not None and record.quality_score >= 0.5:
            return False
        if record.metadata.get("promoted"):
            return False
        last_used = record.last_used_at
        if last_used is None:
            reference = record.approved_at or record.recorded_at
            return reference < cutoff
        return last_used < cutoff

    def _prune_tool_record(self, record: MutationRecord) -> None:
        reclaimed = self._delete_tool_files(record.name)
        try:
            from tools.registry import registry

            registry.deregister_tool(record.name)
        except Exception as exc:
            logger.debug("deregister during prune failed for %s: %s", record.name, exc)
        metadata = dict(record.metadata)
        metadata["pruned"] = True
        self._store._set_status_and_metadata(record.id, "pruned", metadata)
        logger.info("pruned generated tool %s (%s bytes reclaimed)", record.name, reclaimed)

    def _delete_tool_files(self, tool_name: str) -> int:
        generated_dir = self._store.generated_tools_dir()
        reclaimed = 0
        for suffix in (".py", ".sig", ".meta.json"):
            path = generated_dir / f"{tool_name}{suffix}"
            if path.exists():
                try:
                    reclaimed += path.stat().st_size
                    path.unlink()
                except OSError as exc:
                    logger.warning("could not delete %s during prune: %s", path, exc)
        return reclaimed

    def _prune_rolled_back_source(self, dry_run: bool, *, workspace_id: str) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_ROLLED_BACK_RETENTION_DAYS)
        reclaimed = 0
        for record in self._all_records(workspace_id, status="rolled_back"):
            if record.recorded_at >= cutoff or not record.source_code:
                continue
            reclaimed += len(record.source_code.encode("utf-8"))
            if not dry_run:
                self._store.clear_source_code(record.id)
        return reclaimed


_pruner: MutationPruner | None = None


def get_mutation_pruner() -> MutationPruner:
    global _pruner
    if _pruner is None:
        _pruner = MutationPruner()
    return _pruner
