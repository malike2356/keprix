"""Training data export and localization quality metrics (Prompt 50)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix.backend.localization.audit import get_audit_service
from keprix.backend.localization.corrections_store import get_corrections_store
from keprix.backend.localization.store import get_localization_store

SM4T_TASK_TYPES = frozenset({"s2t", "t2t"})
LLM_TASK_TYPES = frozenset({"intent", "entity"})
READINESS_THRESHOLD = 500


@dataclass
class ExportSummary:
    exported_at: str
    total_samples: int
    files: dict[str, int] = field(default_factory=dict)
    domains: list[str] = field(default_factory=list)


class LocalizationFlywheel:
    def __init__(self) -> None:
        self._store = get_corrections_store()

    async def export_sm4t_training_data(
        self,
        output_dir: Path,
        *,
        workspace_id: str = "default",
        domain: str | None = None,
        task_type: str | None = None,
        min_quality_score: int = 3,
        since: datetime | None = None,
    ) -> ExportSummary:
        output_dir.mkdir(parents=True, exist_ok=True)
        samples = await self._store.list_training_samples(
            workspace_id,
            task_type=task_type,
            domain=domain,
            min_quality_score=min_quality_score,
            unexported_only=True,
            since=since,
        )
        sm4t_samples = [sample for sample in samples if sample.get("task_type") in SM4T_TASK_TYPES]
        grouped = self._group_by_task_and_language(sm4t_samples)
        written: dict[str, int] = {}

        for key, group in grouped.items():
            task, src_lang, tgt_lang = key
            filename = self._make_filename(task, src_lang, tgt_lang)
            path = output_dir / filename
            written[filename] = self._write_jsonl(path, task, group)

        sample_ids = [str(sample["id"]) for sample in sm4t_samples]
        await self._store.mark_samples_exported(sample_ids)

        manifest = ExportSummary(
            exported_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            total_samples=len(sm4t_samples),
            files=written,
            domains=sorted({str(sample.get("domain") or "generic") for sample in sm4t_samples}),
        )
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest.__dict__, indent=2),
            encoding="utf-8",
        )
        return manifest

    async def export_llm_correction_data(
        self,
        output_dir: Path,
        *,
        workspace_id: str = "default",
        domain: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        samples = await self._store.list_training_samples(
            workspace_id,
            domain=domain,
            unexported_only=True,
            since=since,
        )
        llm_samples = [sample for sample in samples if sample.get("task_type") in LLM_TASK_TYPES]
        path = output_dir / "intent_entity_corrections.jsonl"
        count = 0
        with path.open("w", encoding="utf-8") as handle:
            for sample in llm_samples:
                correction = await self._store.get_correction(str(sample["correction_id"]))
                audit = None
                if correction:
                    audit = await get_audit_service().get_record(
                        workspace_id,
                        str(correction["audit_record_id"]),
                    )
                record = {
                    "system": "Extract intent and entities from this domain message. Return JSON.",
                    "user": (audit or {}).get("translated_input") or sample.get("source_text"),
                    "assistant": sample.get("target_text"),
                    "domain": sample.get("domain"),
                    "correction_type": sample.get("task_type"),
                }
                handle.write(json.dumps(record) + "\n")
                count += 1
        await self._store.mark_samples_exported([str(sample["id"]) for sample in llm_samples])
        return {"intent_entity_corrections": count, "path": str(path)}

    def _group_by_task_and_language(
        self,
        samples: list[dict[str, Any]],
    ) -> dict[tuple[str, str, str | None], list[dict[str, Any]]]:
        grouped: dict[tuple[str, str, str | None], list[dict[str, Any]]] = defaultdict(list)
        for sample in samples:
            key = (
                str(sample.get("task_type") or "t2t"),
                str(sample.get("source_language") or "en"),
                sample.get("target_language"),
            )
            grouped[key].append(sample)
        return grouped

    def _make_filename(self, task: str, src_lang: str, tgt_lang: str | None) -> str:
        if task == "s2t":
            return f"s2t_{src_lang}.jsonl"
        tgt = tgt_lang or "unknown"
        return f"t2t_{src_lang}_{tgt}.jsonl"

    def _write_jsonl(self, path: Path, task: str, samples: list[dict[str, Any]]) -> int:
        count = 0
        with path.open("w", encoding="utf-8") as handle:
            for sample in samples:
                if task == "t2t":
                    record = {
                        "src_lang": sample.get("source_language"),
                        "tgt_lang": sample.get("target_language"),
                        "src_text": sample.get("source_text"),
                        "tgt_text": sample.get("target_text"),
                        "quality_score": sample.get("quality_score"),
                        "domain": sample.get("domain"),
                    }
                else:
                    audio_id = sample.get("source_audio_file_id")
                    record = {
                        "src_lang": sample.get("source_language"),
                        "audio_path": str(audio_id) if audio_id else "",
                        "transcript": sample.get("target_text"),
                        "quality_score": sample.get("quality_score"),
                        "domain": sample.get("domain"),
                    }
                handle.write(json.dumps(record) + "\n")
                count += 1
        return count


class LocalizationQualityMetrics:
    def __init__(self) -> None:
        self._corrections = get_corrections_store()
        self._localization = get_localization_store()

    async def get_correction_rate(
        self,
        workspace_id: str,
        *,
        language_code: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        audit_rows = await self._localization.list_audit(workspace_id, limit=100000)
        if since:
            audit_rows = [
                row
                for row in audit_rows
                if row.get("created_at")
                and datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00")) >= since
            ]
        if language_code:
            audit_rows = [
                row for row in audit_rows if row.get("detected_language") == language_code
            ]
        total_audit = len(audit_rows)
        corrections = await self._corrections.list_corrections(
            workspace_id,
            source_language=language_code,
            limit=100000,
        )
        if since:
            corrections = [
                row
                for row in corrections
                if row.get("submitted_at")
                and datetime.fromisoformat(str(row["submitted_at"]).replace("Z", "+00:00")) >= since
            ]
        approved = [row for row in corrections if row.get("status") == "approved"]
        by_type = Counter(str(row.get("correction_type") or "unknown") for row in approved)
        rate = (len(approved) / total_audit) if total_audit else 0.0
        return {
            "workspace_id": workspace_id,
            "language_code": language_code,
            "audit_records": total_audit,
            "corrections_total": len(corrections),
            "corrections_approved": len(approved),
            "correction_rate": round(rate, 4),
            "by_type": dict(by_type),
        }

    async def get_provider_accuracy_by_language(self, workspace_id: str = "default") -> dict[str, Any]:
        audit_rows = await self._localization.list_audit(workspace_id, limit=100000)
        corrections = await self._corrections.list_corrections(workspace_id, status="approved", limit=100000)
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"total_responses": 0, "total_corrections": 0}
        )
        for row in audit_rows:
            provider = str(row.get("translation_provider") or row.get("transcription_provider") or "unknown")
            language = str(row.get("detected_language") or "unknown")
            month = str(row.get("created_at") or "")[:7]
            key = f"{provider}|{language}|{month}"
            grouped[key]["total_responses"] += 1
            grouped[key]["provider"] = provider
            grouped[key]["language"] = language
            grouped[key]["month"] = month
        for row in corrections:
            audit = await self._localization.get_audit_record(workspace_id, str(row["audit_record_id"]))
            provider = str((audit or {}).get("translation_provider") or "unknown")
            language = str(row.get("source_language") or "unknown")
            month = str(row.get("submitted_at") or "")[:7]
            key = f"{provider}|{language}|{month}"
            grouped[key]["total_corrections"] += 1
        results = []
        for stats in grouped.values():
            total = stats["total_responses"]
            corrections_count = stats["total_corrections"]
            rate = (corrections_count / total) if total else 0.0
            results.append(
                {
                    **stats,
                    "correction_rate": round(rate, 4),
                    "needs_investigation": rate > 0.10 and total >= 5,
                }
            )
        return {"providers": results}

    async def get_most_corrected_terms(
        self,
        *,
        workspace_id: str = "default",
        domain: str,
        language_code: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        rows = await self._corrections.list_corrections(
            workspace_id,
            status="approved",
            source_language=language_code,
            domain=domain,
            limit=100000,
        )
        counter = Counter(str(row.get("original_value") or "") for row in rows)
        results = []
        for term, count in counter.most_common(limit):
            if not term:
                continue
            results.append({"term": term, "correction_count": count})
        return results

    async def get_coverage_summary(self, workspace_id: str) -> dict[str, Any]:
        audit_rows = await self._localization.list_audit(workspace_id, limit=100000)
        corrections = await self._corrections.list_corrections(workspace_id, limit=100000)
        samples = await self._corrections.list_training_samples(workspace_id, limit=100000)
        exported = [sample for sample in samples if sample.get("included_in_export_at")]
        languages = sorted(
            {
                str(row.get("detected_language") or row.get("source_language") or "unknown")
                for row in audit_rows
            }
            | {
                str(row.get("source_language") or "unknown")
                for row in corrections
            }
        )
        readiness: dict[str, Any] = {}
        for language in languages:
            staged = [
                sample
                for sample in samples
                if sample.get("source_language") == language and sample.get("task_type") in SM4T_TASK_TYPES
            ]
            readiness[language] = {
                "staged_samples": len(staged),
                "exported_samples": len(
                    [sample for sample in exported if sample.get("source_language") == language]
                ),
                "ready_for_export": len(staged) >= READINESS_THRESHOLD,
                "threshold": READINESS_THRESHOLD,
            }
        by_type = Counter(str(row.get("correction_type") or "unknown") for row in corrections)
        return {
            "workspace_id": workspace_id,
            "interaction_count": len(audit_rows),
            "correction_count": len(corrections),
            "correction_by_type": dict(by_type),
            "training_samples_staged": len(samples),
            "training_samples_exported": len(exported),
            "languages": languages,
            "readiness_by_language": readiness,
        }


_flywheel: LocalizationFlywheel | None = None
_metrics: LocalizationQualityMetrics | None = None


def get_flywheel() -> LocalizationFlywheel:
    global _flywheel
    if _flywheel is None:
        _flywheel = LocalizationFlywheel()
    return _flywheel


def get_quality_metrics() -> LocalizationQualityMetrics:
    global _metrics
    if _metrics is None:
        _metrics = LocalizationQualityMetrics()
    return _metrics
