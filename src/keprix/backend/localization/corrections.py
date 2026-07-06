"""Localization correction queue and approval workflow (Prompt 50)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from keprix.backend.localization.audit import get_audit_service
from keprix.backend.localization.corrections_store import get_corrections_store
from keprix.backend.localization.glossary import get_glossary_service
from keprix.backend.localization.notifications import notify_localization_correction
from keprix.backend.localization.translation_cache import translation_cache_override

CORRECTION_TYPES = frozenset(
    {
        "transcription",
        "translation",
        "intent",
        "entity",
        "response_translation",
        "glossary_addition",
    }
)

SM4T_TASK_TYPES = {
    "transcription": "s2t",
    "translation": "t2t",
    "response_translation": "t2t",
}


@dataclass
class CorrectionRecord:
    id: str
    audit_record_id: str
    workspace_id: str
    correction_type: str
    original_value: str
    corrected_value: str
    source_language: str
    target_language: str | None
    domain: str
    status: str
    submitted_by_user_id: str | None = None
    submitted_at: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: str | None = None
    rejection_reason: str | None = None
    applied_to_glossary: bool = False
    staged_for_training: bool = False
    training_sample_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorrectionRecord:
        return cls(
            id=str(data["id"]),
            audit_record_id=str(data["audit_record_id"]),
            workspace_id=str(data["workspace_id"]),
            correction_type=str(data["correction_type"]),
            original_value=str(data["original_value"]),
            corrected_value=str(data["corrected_value"]),
            source_language=str(data["source_language"]),
            target_language=data.get("target_language"),
            domain=str(data.get("domain") or "generic"),
            status=str(data.get("status") or "pending"),
            submitted_by_user_id=data.get("submitted_by_user_id"),
            submitted_at=data.get("submitted_at"),
            reviewed_by_user_id=data.get("reviewed_by_user_id"),
            reviewed_at=data.get("reviewed_at"),
            rejection_reason=data.get("rejection_reason"),
            applied_to_glossary=bool(data.get("applied_to_glossary")),
            staged_for_training=bool(data.get("staged_for_training")),
            training_sample_id=data.get("training_sample_id"),
        )


class LocalizationCorrectionQueue:
    def __init__(self) -> None:
        self._store = get_corrections_store()

    async def submit_user_correction(
        self,
        *,
        audit_record_id: str,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        workspace_id: str,
        source_language: str,
        target_language: str | None = None,
        domain: str = "generic",
    ) -> CorrectionRecord:
        self._validate_type(correction_type)
        record = await self._insert_correction(
            audit_record_id=audit_record_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            workspace_id=workspace_id,
            source_language=source_language,
            target_language=target_language,
            domain=domain,
            submitted_by_user_id=None,
        )
        await notify_localization_correction(
            workspace_id=workspace_id,
            correction_type=correction_type,
            correction_id=record.id,
        )
        return record

    async def submit_operator_correction(
        self,
        *,
        audit_record_id: str,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        workspace_id: str,
        operator_user_id: str,
        source_language: str,
        target_language: str | None = None,
        domain: str = "generic",
        auto_approve: bool = True,
    ) -> CorrectionRecord:
        self._validate_type(correction_type)
        record = await self._insert_correction(
            audit_record_id=audit_record_id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            workspace_id=workspace_id,
            source_language=source_language,
            target_language=target_language,
            domain=domain,
            submitted_by_user_id=operator_user_id,
        )
        if auto_approve:
            record = await self.approve_correction(record.id, operator_user_id)
        return record

    async def approve_correction(
        self,
        correction_id: str,
        reviewer_user_id: str,
        *,
        quality_score: int = 3,
        corrected_value: str | None = None,
    ) -> CorrectionRecord:
        patch: dict[str, Any] = {
            "status": "approved",
            "reviewed_by_user_id": reviewer_user_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        if corrected_value is not None:
            patch["corrected_value"] = corrected_value
        updated = await self._store.update_correction(correction_id, patch)
        if updated is None:
            raise ValueError(f"Correction not found: {correction_id}")
        correction = CorrectionRecord.from_dict(updated)
        await self._apply_immediate_effects(correction)
        await self._stage_for_training(correction, quality_score)
        refreshed = await self._store.get_correction(correction_id)
        return CorrectionRecord.from_dict(refreshed or updated)

    async def reject_correction(
        self,
        correction_id: str,
        reviewer_user_id: str,
        *,
        reason: str,
    ) -> CorrectionRecord:
        updated = await self._store.update_correction(
            correction_id,
            {
                "status": "rejected",
                "reviewed_by_user_id": reviewer_user_id,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "rejection_reason": reason,
            },
        )
        if updated is None:
            raise ValueError(f"Correction not found: {correction_id}")
        return CorrectionRecord.from_dict(updated)

    async def batch_approve(
        self,
        correction_ids: list[str],
        reviewer_user_id: str,
        *,
        quality_score: int = 3,
    ) -> list[CorrectionRecord]:
        results: list[CorrectionRecord] = []
        for correction_id in correction_ids:
            results.append(
                await self.approve_correction(
                    correction_id,
                    reviewer_user_id,
                    quality_score=quality_score,
                )
            )
        return results

    async def get(self, correction_id: str) -> CorrectionRecord | None:
        row = await self._store.get_correction(correction_id)
        return CorrectionRecord.from_dict(row) if row else None

    async def list_corrections(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        correction_type: str | None = None,
        source_language: str | None = None,
        domain: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = await self._store.list_corrections(
            workspace_id,
            status=status,
            correction_type=correction_type,
            source_language=source_language,
            domain=domain,
            limit=limit,
            offset=offset,
        )
        enriched: list[dict[str, Any]] = []
        audit = get_audit_service()
        for row in rows:
            audit_record = await audit.get_record(workspace_id, str(row["audit_record_id"]))
            enriched.append({**row, "audit_record": audit_record})
        return enriched

    async def _insert_correction(
        self,
        *,
        audit_record_id: str,
        correction_type: str,
        original_value: str,
        corrected_value: str,
        workspace_id: str,
        source_language: str,
        target_language: str | None,
        domain: str,
        submitted_by_user_id: str | None,
    ) -> CorrectionRecord:
        row = await self._store.insert_correction(
            {
                "audit_record_id": audit_record_id,
                "correction_type": correction_type,
                "original_value": original_value,
                "corrected_value": corrected_value,
                "workspace_id": workspace_id,
                "source_language": source_language,
                "target_language": target_language,
                "domain": domain,
                "submitted_by_user_id": submitted_by_user_id,
                "status": "pending",
            }
        )
        return CorrectionRecord.from_dict(row)

    async def _apply_immediate_effects(self, correction: CorrectionRecord) -> None:
        if correction.correction_type == "glossary_addition":
            await get_glossary_service().upsert_term(
                domain=correction.domain,
                source_language=correction.source_language,
                source_term=correction.original_value,
                translated_term=correction.corrected_value,
                workspace_id=correction.workspace_id,
            )
            await self._store.update_correction(
                correction.id,
                {"applied_to_glossary": True},
            )
        elif correction.correction_type in {"translation", "response_translation"}:
            if correction.target_language:
                await translation_cache_override.set_override(
                    correction.workspace_id,
                    correction.source_language,
                    correction.target_language,
                    correction.original_value,
                    correction.corrected_value,
                )

    async def _stage_for_training(self, correction: CorrectionRecord, quality_score: int) -> None:
        task_type = SM4T_TASK_TYPES.get(correction.correction_type)
        if correction.correction_type in {"intent", "entity"}:
            sample = await self._store.insert_training_sample(
                {
                    "workspace_id": correction.workspace_id,
                    "correction_id": correction.id,
                    "task_type": correction.correction_type,
                    "source_language": correction.source_language,
                    "target_language": correction.target_language,
                    "source_text": correction.original_value,
                    "target_text": correction.corrected_value,
                    "domain": correction.domain,
                    "quality_score": quality_score,
                }
            )
            await self._store.update_correction(
                correction.id,
                {
                    "staged_for_training": True,
                    "training_sample_id": sample["id"],
                },
            )
            return

        if not task_type:
            return

        audit_record = await get_audit_service().get_record(
            correction.workspace_id,
            correction.audit_record_id,
        )
        sample = await self._store.insert_training_sample(
            {
                "workspace_id": correction.workspace_id,
                "correction_id": correction.id,
                "task_type": task_type,
                "source_language": correction.source_language,
                "target_language": correction.target_language,
                "source_text": correction.original_value if task_type == "t2t" else None,
                "source_audio_file_id": (audit_record or {}).get("audio_file_id"),
                "target_text": correction.corrected_value,
                "domain": correction.domain,
                "quality_score": quality_score,
            }
        )
        await self._store.update_correction(
            correction.id,
            {
                "staged_for_training": True,
                "training_sample_id": sample["id"],
            },
        )

    def _validate_type(self, correction_type: str) -> None:
        if correction_type not in CORRECTION_TYPES:
            raise ValueError(f"Unsupported correction_type: {correction_type}")


_queue: LocalizationCorrectionQueue | None = None


def get_correction_queue() -> LocalizationCorrectionQueue:
    global _queue
    if _queue is None:
        _queue = LocalizationCorrectionQueue()
    return _queue
