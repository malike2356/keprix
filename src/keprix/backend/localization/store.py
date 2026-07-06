"""JSON and PostgreSQL persistence for localization."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from keprix.backend.localization.models import (
    LocalizationAuditRow,
    UserLanguagePreferenceRow,
    audit_row_to_dict,
    ensure_localization_tables,
    preference_row_to_dict,
)
from keprix.database import get_session_factory


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_dir() -> Path:
    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "localization"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "localization"
        except Exception:
            root = Path.home() / ".keprix" / "localization"
    root.mkdir(parents=True, exist_ok=True)
    (root / "glossaries").mkdir(exist_ok=True)
    return root


class LocalizationStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _data_dir()

    def _preferences_path(self, workspace_id: str) -> Path:
        return self._dir / f"preferences_{workspace_id}.json"

    def _audit_path(self, workspace_id: str) -> Path:
        return self._dir / f"audit_{workspace_id}.jsonl"

    def _overrides_path(self, workspace_id: str) -> Path:
        return self._dir / f"translation_overrides_{workspace_id}.json"

    def _glossary_path(self, glossary_id: str) -> Path:
        return self._dir / "glossaries" / f"{glossary_id}.json"

    async def get_preferences(self, workspace_id: str, user_id: str) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            return self._file_get_preferences(workspace_id, user_id)
        await ensure_localization_tables()
        async with factory() as session:
            result = await session.execute(
                select(UserLanguagePreferenceRow).where(
                    UserLanguagePreferenceRow.workspace_id == workspace_id,
                    UserLanguagePreferenceRow.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return preference_row_to_dict(row)

    def _file_get_preferences(self, workspace_id: str, user_id: str) -> dict[str, Any] | None:
        path = self._preferences_path(workspace_id)
        if not path.exists():
            return None
        rows = json.loads(path.read_text(encoding="utf-8"))
        return rows.get(user_id)

    async def upsert_preferences(
        self,
        workspace_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        factory = get_session_factory()
        if factory is None:
            return self._file_upsert_preferences(workspace_id, user_id, data)
        await ensure_localization_tables()
        now = datetime.now(timezone.utc)
        async with factory() as session:
            result = await session.execute(
                select(UserLanguagePreferenceRow).where(
                    UserLanguagePreferenceRow.workspace_id == workspace_id,
                    UserLanguagePreferenceRow.user_id == user_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = UserLanguagePreferenceRow(
                    id=str(uuid.uuid4()),
                    workspace_id=workspace_id,
                    user_id=user_id,
                    created_at=now,
                )
                session.add(row)
            existing = preference_row_to_dict(row)
            merged = {
                **existing,
                **data,
                "workspace_id": workspace_id,
                "user_id": user_id,
                "updated_at": now.isoformat(),
            }
            row.preferred_input_language = merged.get("preferred_input_language")
            row.preferred_output_language = merged.get("preferred_output_language")
            row.voice_output_enabled = bool(merged.get("voice_output_enabled", False))
            row.preferred_voice_id = merged.get("preferred_voice_id")
            row.bilingual_replies = bool(merged.get("bilingual_replies", False))
            row.updated_at = now
            await session.commit()
            await session.refresh(row)
            return preference_row_to_dict(row)

    def _file_upsert_preferences(
        self,
        workspace_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        path = self._preferences_path(workspace_id)
        rows: dict[str, Any] = {}
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        existing = rows.get(user_id) or {}
        merged = {
            **existing,
            **data,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "updated_at": _utcnow(),
        }
        if "id" not in merged:
            merged["id"] = str(uuid.uuid4())
        if "created_at" not in merged:
            merged["created_at"] = _utcnow()
        rows[user_id] = merged
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return merged

    async def list_preferences(self, workspace_id: str) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            path = self._preferences_path(workspace_id)
            if not path.exists():
                return []
            return list(json.loads(path.read_text(encoding="utf-8")).values())
        await ensure_localization_tables()
        async with factory() as session:
            result = await session.execute(
                select(UserLanguagePreferenceRow).where(
                    UserLanguagePreferenceRow.workspace_id == workspace_id
                )
            )
            return [preference_row_to_dict(row) for row in result.scalars().all()]

    async def append_audit(self, workspace_id: str, record: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **record,
            "id": record.get("id") or str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "created_at": record.get("created_at") or _utcnow(),
        }
        factory = get_session_factory()
        if factory is None:
            path = self._audit_path(workspace_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload) + "\n")
            return payload

        await ensure_localization_tables()
        created_at = datetime.now(timezone.utc)
        async with factory() as session:
            row = LocalizationAuditRow(
                id=str(payload["id"]),
                workspace_id=workspace_id,
                user_id=payload.get("user_id"),
                channel=str(payload.get("channel") or "unknown"),
                request_id=str(payload.get("request_id") or payload["id"]),
                input_type=str(payload.get("input_type") or "text"),
                original_text=payload.get("original_text"),
                translated_input=payload.get("translated_input"),
                final_response=payload.get("final_response"),
                detected_language=payload.get("detected_language"),
                output_language=payload.get("output_language"),
                detection_confidence=payload.get("detection_confidence"),
                transcription_provider=payload.get("transcription_provider"),
                translation_provider=payload.get("translation_provider"),
                speech_provider=payload.get("speech_provider"),
                glossary_id=payload.get("glossary_id"),
                glossary_warnings=payload.get("glossary_warnings") or [],
                human_review_required=bool(payload.get("human_review_required", False)),
                created_at=created_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return audit_row_to_dict(row)

    async def list_audit(
        self,
        workspace_id: str,
        *,
        limit: int = 50,
        human_review_required: bool | None = None,
    ) -> list[dict[str, Any]]:
        factory = get_session_factory()
        if factory is None:
            path = self._audit_path(workspace_id)
            if not path.exists():
                return []
            rows: list[dict[str, Any]] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if human_review_required is not None and row.get("human_review_required") != human_review_required:
                    continue
                rows.append(row)
            return rows[-limit:][::-1]

        await ensure_localization_tables()
        async with factory() as session:
            query = (
                select(LocalizationAuditRow)
                .where(LocalizationAuditRow.workspace_id == workspace_id)
                .order_by(LocalizationAuditRow.created_at.desc())
                .limit(limit)
            )
            if human_review_required is not None:
                query = query.where(
                    LocalizationAuditRow.human_review_required == human_review_required
                )
            result = await session.execute(query)
            return [audit_row_to_dict(row) for row in result.scalars().all()]

    async def get_audit_record(self, workspace_id: str, audit_id: str) -> dict[str, Any] | None:
        factory = get_session_factory()
        if factory is None:
            path = self._audit_path(workspace_id)
            if not path.exists():
                return None
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("id") == audit_id:
                    return row
            return None

        await ensure_localization_tables()
        async with factory() as session:
            result = await session.execute(
                select(LocalizationAuditRow).where(LocalizationAuditRow.id == audit_id)
            )
            row = result.scalar_one_or_none()
            return audit_row_to_dict(row) if row else None

    def get_glossary(self, glossary_id: str) -> dict[str, Any] | None:
        path = self._glossary_path(glossary_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_glossary(self, glossary: dict[str, Any]) -> dict[str, Any]:
        glossary_id = str(glossary.get("id") or glossary.get("glossary_id") or uuid.uuid4())
        payload = {**glossary, "id": glossary_id, "updated_at": _utcnow()}
        if "created_at" not in payload:
            payload["created_at"] = _utcnow()
        path = self._glossary_path(glossary_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def list_glossaries(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for path in sorted((self._dir / "glossaries").glob("*.json")):
            results.append(json.loads(path.read_text(encoding="utf-8")))
        return results

    def get_translation_override(
        self,
        workspace_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
    ) -> str | None:
        path = self._overrides_path(workspace_id)
        if not path.exists():
            return None
        rows = json.loads(path.read_text(encoding="utf-8"))
        key = f"{source_language}|{target_language}|{source_text}"
        return rows.get(key)

    def set_translation_override(
        self,
        workspace_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
        corrected_text: str,
    ) -> None:
        path = self._overrides_path(workspace_id)
        rows: dict[str, str] = {}
        if path.exists():
            rows = json.loads(path.read_text(encoding="utf-8"))
        key = f"{source_language}|{target_language}|{source_text}"
        rows[key] = corrected_text
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


_store: LocalizationStore | None = None


def get_localization_store() -> LocalizationStore:
    global _store
    if _store is None:
        _store = LocalizationStore()
    return _store


def reset_localization_store() -> None:
    global _store
    _store = None
