"""Persistence for localization corrections and training samples (Prompt 50)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select, update

from keprix.backend.localization.models import (
    LocalizationCorrectionRow,
    LocalizationTrainingSampleRow,
    correction_row_to_dict,
    ensure_localization_tables,
    training_sample_row_to_dict,
)
from keprix.database import get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _flywheel_dir() -> Path:
    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "localization" / "flywheel"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "localization" / "flywheel"
        except Exception:
            root = Path.home() / ".keprix" / "localization" / "flywheel"
    root.mkdir(parents=True, exist_ok=True)
    return root


class CorrectionsStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _flywheel_dir()

    def _corrections_path(self, workspace_id: str) -> Path:
        return self._dir / f"corrections_{workspace_id}.jsonl"

    def _samples_path(self, workspace_id: str) -> Path:
        return self._dir / f"training_samples_{workspace_id}.jsonl"

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    async def insert_correction(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **data,
            "id": data.get("id") or str(uuid.uuid4()),
            "status": data.get("status") or "pending",
            "submitted_at": data.get("submitted_at") or _iso(_utcnow()),
            "applied_to_glossary": bool(data.get("applied_to_glossary", False)),
            "staged_for_training": bool(data.get("staged_for_training", False)),
        }
        factory = get_session_factory()
        if factory is None:
            self._append_jsonl(self._corrections_path(payload["workspace_id"]), payload)
            return payload

        await ensure_localization_tables()
        submitted_at = _utcnow()
        async with factory() as session:
            row = LocalizationCorrectionRow(
                id=str(payload["id"]),
                audit_record_id=str(payload["audit_record_id"]),
                workspace_id=str(payload["workspace_id"]),
                correction_type=str(payload["correction_type"]),
                original_value=str(payload["original_value"]),
                corrected_value=str(payload["corrected_value"]),
                source_language=str(payload["source_language"]),
                target_language=payload.get("target_language"),
                domain=str(payload.get("domain") or "generic"),
                submitted_by_user_id=payload.get("submitted_by_user_id"),
                submitted_at=submitted_at,
                status=str(payload["status"]),
                applied_to_glossary=bool(payload["applied_to_glossary"]),
                staged_for_training=bool(payload["staged_for_training"]),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return correction_row_to_dict(row)

    async def get_correction(self, correction_id: str) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            for path in self._dir.glob("corrections_*.jsonl"):
                for row in self._read_jsonl(path):
                    if row.get("id") == correction_id:
                        return row
            return None

        await ensure_localization_tables()
        async with factory() as session:
            result = await session.execute(
                select(LocalizationCorrectionRow).where(LocalizationCorrectionRow.id == correction_id)
            )
            row = result.scalar_one_or_none()
            return correction_row_to_dict(row) if row else None

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
        factory = get_session_factory()
        if factory is None:
            rows = self._read_jsonl(self._corrections_path(workspace_id))
            filtered = [
                row
                for row in rows
                if (status is None or row.get("status") == status)
                and (correction_type is None or row.get("correction_type") == correction_type)
                and (source_language is None or row.get("source_language") == source_language)
                and (domain is None or row.get("domain") == domain)
            ]
            return filtered[offset : offset + limit][::-1]

        await ensure_localization_tables()
        async with factory() as session:
            query = select(LocalizationCorrectionRow).where(
                LocalizationCorrectionRow.workspace_id == workspace_id
            )
            if status:
                query = query.where(LocalizationCorrectionRow.status == status)
            if correction_type:
                query = query.where(LocalizationCorrectionRow.correction_type == correction_type)
            if source_language:
                query = query.where(LocalizationCorrectionRow.source_language == source_language)
            if domain:
                query = query.where(LocalizationCorrectionRow.domain == domain)
            query = query.order_by(LocalizationCorrectionRow.submitted_at.desc()).offset(offset).limit(limit)
            result = await session.execute(query)
            return [correction_row_to_dict(row) for row in result.scalars().all()]

    async def update_correction(self, correction_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            for path in self._dir.glob("corrections_*.jsonl"):
                rows = self._read_jsonl(path)
                updated: dict[str, Any] | None = None
                for index, row in enumerate(rows):
                    if row.get("id") == correction_id:
                        rows[index] = {**row, **patch}
                        updated = rows[index]
                        break
                if updated:
                    self._write_jsonl(path, rows)
                    return updated
            return None

        await ensure_localization_tables()
        async with factory() as session:
            result = await session.execute(
                select(LocalizationCorrectionRow).where(LocalizationCorrectionRow.id == correction_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            for key, value in patch.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            await session.commit()
            await session.refresh(row)
            return correction_row_to_dict(row)

    async def insert_training_sample(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **data,
            "id": data.get("id") or str(uuid.uuid4()),
            "created_at": data.get("created_at") or _iso(_utcnow()),
            "quality_score": int(data.get("quality_score") or 3),
        }
        factory = get_session_factory()
        workspace_id = str(data.get("workspace_id") or "default")
        if factory is None:
            self._append_jsonl(self._samples_path(workspace_id), payload)
            return payload

        await ensure_localization_tables()
        created_at = _utcnow()
        async with factory() as session:
            row = LocalizationTrainingSampleRow(
                id=str(payload["id"]),
                correction_id=str(payload["correction_id"]),
                task_type=str(payload["task_type"]),
                source_language=str(payload["source_language"]),
                target_language=payload.get("target_language"),
                source_text=payload.get("source_text"),
                source_audio_file_id=payload.get("source_audio_file_id"),
                target_text=str(payload["target_text"]),
                domain=str(payload.get("domain") or "generic"),
                quality_score=int(payload["quality_score"]),
                created_at=created_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return training_sample_row_to_dict(row)

    async def list_training_samples(
        self,
        workspace_id: str,
        *,
        task_type: str | None = None,
        domain: str | None = None,
        min_quality_score: int = 1,
        unexported_only: bool = False,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            rows = self._read_jsonl(self._samples_path(workspace_id))
            results: list[dict[str, Any]] = []
            for row in rows:
                if task_type and row.get("task_type") != task_type:
                    continue
                if domain and row.get("domain") != domain:
                    continue
                if int(row.get("quality_score") or 0) < min_quality_score:
                    continue
                if unexported_only and row.get("included_in_export_at"):
                    continue
                if since and row.get("created_at"):
                    created = datetime.fromisoformat(str(row["created_at"]).replace("Z", "+00:00"))
                    if created < since:
                        continue
                results.append(row)
            return results

        await ensure_localization_tables()
        async with factory() as session:
            query = select(LocalizationTrainingSampleRow)
            if task_type:
                query = query.where(LocalizationTrainingSampleRow.task_type == task_type)
            if domain:
                query = query.where(LocalizationTrainingSampleRow.domain == domain)
            query = query.where(LocalizationTrainingSampleRow.quality_score >= min_quality_score)
            if unexported_only:
                query = query.where(LocalizationTrainingSampleRow.included_in_export_at.is_(None))
            if since:
                query = query.where(LocalizationTrainingSampleRow.created_at >= since)
            result = await session.execute(query)
            return [training_sample_row_to_dict(row) for row in result.scalars().all()]

    async def mark_samples_exported(self, sample_ids: list[str]) -> None:
        if not sample_ids:
            return
        now = _utcnow()
        factory = get_session_factory()
        if factory is None:
            for path in self._dir.glob("training_samples_*.jsonl"):
                rows = self._read_jsonl(path)
                changed = False
                for row in rows:
                    if row.get("id") in sample_ids:
                        row["included_in_export_at"] = _iso(now)
                        changed = True
                if changed:
                    self._write_jsonl(path, rows)
            return

        await ensure_localization_tables()
        async with factory() as session:
            await session.execute(
                update(LocalizationTrainingSampleRow)
                .where(LocalizationTrainingSampleRow.id.in_(sample_ids))
                .values(included_in_export_at=now)
            )
            await session.commit()

    async def count_corrections(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        correction_type: str | None = None,
        source_language: str | None = None,
        since: datetime | None = None,
    ) -> int:
        rows = await self.list_corrections(
            workspace_id,
            status=status,
            correction_type=correction_type,
            source_language=source_language,
            limit=100000,
        )
        if since is None:
            return len(rows)
        count = 0
        for row in rows:
            submitted = row.get("submitted_at")
            if not submitted:
                continue
            created = datetime.fromisoformat(str(submitted).replace("Z", "+00:00"))
            if created >= since:
                count += 1
        return count


_store: CorrectionsStore | None = None


def get_corrections_store() -> CorrectionsStore:
    global _store
    if _store is None:
        _store = CorrectionsStore()
    return _store


def reset_corrections_store() -> None:
    global _store
    _store = None
