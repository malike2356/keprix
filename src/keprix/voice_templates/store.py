"""Persistent store for voice template metadata and audio files."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from keprix.voice_templates.audio_utils import validate_wav_format
from keprix.voice_templates.categories import DEFAULT_LANGUAGE_FALLBACKS, GENERIC_CATEGORIES
from keprix.voice_templates.schemas import CategoryCreate, TemplateStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _data_root() -> Path:
    base = Path(os.environ.get("KEPRIX_DATA_DIR", "/data/keprix"))
    root = base / "voice-templates"
    root.mkdir(parents=True, exist_ok=True)
    (root / "audio").mkdir(exist_ok=True)
    (root / "temp").mkdir(exist_ok=True)
    return root


@dataclass
class CategoryRecord:
    id: str
    label: str
    description: str | None
    domain: str
    is_dynamic: bool
    dynamic_placeholder: str | None
    sort_order: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TemplateRecord:
    id: str
    category_id: str
    language_code: str
    dialect_note: str | None
    audio_file_id: str
    transcript: str
    transcript_english: str
    duration_seconds: float
    recorded_by: str | None
    recorded_at: date | None
    quality_rating: int | None
    status: TemplateStatus
    approved_by_user_id: str | None
    approved_at: datetime | None
    rejection_reason: str | None
    play_count: int
    workspace_id: str | None
    created_at: datetime

    def to_dict(self, *, audio_url: str | None = None) -> dict[str, Any]:
        payload = {
            "id": self.id,
            "category_id": self.category_id,
            "language_code": self.language_code,
            "dialect_note": self.dialect_note,
            "audio_file_id": self.audio_file_id,
            "transcript": self.transcript,
            "transcript_english": self.transcript_english,
            "duration_seconds": self.duration_seconds,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "quality_rating": self.quality_rating,
            "status": self.status,
            "approved_by_user_id": self.approved_by_user_id,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "play_count": self.play_count,
            "workspace_id": self.workspace_id,
            "created_at": self.created_at.isoformat(),
            "audio_url": audio_url,
        }
        return payload


class VoiceTemplateStore:
    def __init__(self) -> None:
        self._root = _data_root()
        self._state_path = self._root / "state.json"
        self.categories: dict[str, CategoryRecord] = {}
        self.templates: dict[str, TemplateRecord] = {}
        self.language_fallbacks: dict[str, str] = dict(DEFAULT_LANGUAGE_FALLBACKS)
        self._temp_files: dict[str, Path] = {}
        self._seed_categories()
        self._load()

    def _seed_categories(self) -> None:
        for cat in GENERIC_CATEGORIES:
            self._upsert_category(cat)

    def _upsert_category(self, body: CategoryCreate) -> CategoryRecord:
        record = CategoryRecord(
            id=body.id,
            label=body.label,
            description=body.description,
            domain=body.domain,
            is_dynamic=body.is_dynamic,
            dynamic_placeholder=body.dynamic_placeholder,
            sort_order=body.sort_order,
        )
        self.categories[body.id] = record
        return record

    def register_category(self, body: CategoryCreate) -> CategoryRecord:
        record = self._upsert_category(body)
        self._save()
        return record

    def list_categories(self, domain: str | None = None) -> list[CategoryRecord]:
        rows = list(self.categories.values())
        if domain:
            rows = [r for r in rows if r.domain == domain]
        return sorted(rows, key=lambda r: (r.sort_order, r.id))

    def get_category(self, category_id: str) -> CategoryRecord | None:
        return self.categories.get(category_id)

    def is_dynamic_category(self, category_id: str) -> bool:
        cat = self.categories.get(category_id)
        return bool(cat and cat.is_dynamic)

    def _load(self) -> None:
        if not self._state_path.exists():
            return
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for item in raw.get("categories", []):
            if item.get("id") and item["id"] not in self.categories:
                self.categories[item["id"]] = CategoryRecord(**item)
        self.language_fallbacks.update(raw.get("language_fallbacks", {}))
        for item in raw.get("templates", []):
            if item.get("recorded_at"):
                item["recorded_at"] = date.fromisoformat(item["recorded_at"])
            if item.get("approved_at"):
                item["approved_at"] = datetime.fromisoformat(item["approved_at"])
            if item.get("created_at"):
                item["created_at"] = datetime.fromisoformat(item["created_at"])
            self.templates[item["id"]] = TemplateRecord(**item)

    def _save(self) -> None:
        payload = {
            "categories": [c.to_dict() for c in self.categories.values()],
            "language_fallbacks": self.language_fallbacks,
            "templates": [
                {
                    **t.to_dict(),
                    "recorded_at": t.recorded_at.isoformat() if t.recorded_at else None,
                    "approved_at": t.approved_at.isoformat() if t.approved_at else None,
                    "created_at": t.created_at.isoformat(),
                }
                for t in self.templates.values()
            ],
        }
        tmp = self._state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._state_path)

    def save_audio(self, audio_bytes: bytes, *, workspace_id: str | None) -> str:
        validate_wav_format(audio_bytes)
        audio_id = str(uuid.uuid4())
        prefix = workspace_id or "system"
        dest = self._root / "audio" / prefix / f"{audio_id}.wav"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(audio_bytes)
        return audio_id

    def get_audio_bytes(self, audio_file_id: str, workspace_id: str | None = None) -> bytes | None:
        for prefix in (workspace_id, "system", None):
            if prefix is None:
                matches = list((self._root / "audio").rglob(f"{audio_file_id}.wav"))
                if matches:
                    return matches[0].read_bytes()
                continue
            path = self._root / "audio" / prefix / f"{audio_file_id}.wav"
            if path.exists():
                return path.read_bytes()
        return None

    def save_temp_audio(self, audio_bytes: bytes, language_code: str) -> str:
        token = str(uuid.uuid4())
        path = self._root / "temp" / f"{token}.wav"
        path.write_bytes(audio_bytes)
        self._temp_files[token] = path
        return token

    def get_temp_path(self, token: str) -> Path | None:
        path = self._root / "temp" / f"{token}.wav"
        return path if path.exists() else None

    def create_template(
        self,
        *,
        category_id: str,
        language_code: str,
        audio_file_id: str,
        transcript: str,
        transcript_english: str,
        duration_seconds: float,
        recorded_by: str | None,
        recorded_at: date | None,
        dialect_note: str | None,
        workspace_id: str | None,
        status: TemplateStatus = "pending",
        quality_rating: int | None = None,
        approved_by_user_id: str | None = None,
    ) -> TemplateRecord:
        template_id = str(uuid.uuid4())
        record = TemplateRecord(
            id=template_id,
            category_id=category_id,
            language_code=language_code.lower(),
            dialect_note=dialect_note,
            audio_file_id=audio_file_id,
            transcript=transcript,
            transcript_english=transcript_english,
            duration_seconds=duration_seconds,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            quality_rating=quality_rating,
            status=status,
            approved_by_user_id=approved_by_user_id,
            approved_at=_utcnow() if status == "approved" else None,
            rejection_reason=None,
            play_count=0,
            workspace_id=workspace_id,
            created_at=_utcnow(),
        )
        self.templates[template_id] = record
        self._save()
        return record

    def get_template(self, template_id: str) -> TemplateRecord | None:
        return self.templates.get(template_id)

    def list_templates(
        self,
        *,
        language_code: str | None = None,
        category_id: str | None = None,
        status: TemplateStatus | None = None,
        workspace_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TemplateRecord]:
        rows = list(self.templates.values())
        if language_code:
            rows = [r for r in rows if r.language_code == language_code.lower()]
        if category_id:
            rows = [r for r in rows if r.category_id == category_id]
        if status:
            rows = [r for r in rows if r.status == status]
        if workspace_id is not None:
            rows = [r for r in rows if r.workspace_id == workspace_id]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return rows[offset : offset + limit]

    def find_approved(
        self,
        category_id: str,
        language_code: str,
        workspace_id: str | None,
    ) -> TemplateRecord | None:
        lang = language_code.lower()
        for record in self.templates.values():
            if (
                record.category_id == category_id
                and record.language_code == lang
                and record.status == "approved"
                and record.workspace_id == workspace_id
            ):
                return record
        return None

    def increment_play_count(self, template_id: str) -> None:
        record = self.templates.get(template_id)
        if record is None:
            return
        record.play_count += 1
        self._save()

    def approve_template(
        self,
        template_id: str,
        *,
        approver_user_id: str,
        quality_rating: int,
    ) -> TemplateRecord | None:
        record = self.templates.get(template_id)
        if record is None:
            return None
        for other in self.templates.values():
            if (
                other.id != template_id
                and other.category_id == record.category_id
                and other.language_code == record.language_code
                and other.workspace_id == record.workspace_id
                and other.status == "approved"
            ):
                other.status = "archived"
        record.status = "approved"
        record.approved_by_user_id = approver_user_id
        record.approved_at = _utcnow()
        record.quality_rating = quality_rating
        record.rejection_reason = None
        self._save()
        return record

    def reject_template(self, template_id: str, *, reason: str) -> TemplateRecord | None:
        record = self.templates.get(template_id)
        if record is None:
            return None
        record.status = "rejected"
        record.rejection_reason = reason
        self._save()
        return record

    def archive_template(self, template_id: str) -> TemplateRecord | None:
        record = self.templates.get(template_id)
        if record is None:
            return None
        record.status = "archived"
        self._save()
        return record

    def set_language_fallback(self, language_code: str, fallback_language_code: str) -> None:
        self.language_fallbacks[language_code.lower()] = fallback_language_code.lower()
        self._save()

    def approved_count_for_language(self, language_code: str) -> int:
        lang = language_code.lower()
        categories: set[str] = set()
        for record in self.templates.values():
            if record.language_code == lang and record.status == "approved":
                categories.add(record.category_id)
        return len(categories)


_store: VoiceTemplateStore | None = None


def get_voice_template_store() -> VoiceTemplateStore:
    global _store
    if _store is None:
        _store = VoiceTemplateStore()
    return _store


def reset_voice_template_store() -> None:
    global _store
    _store = None
