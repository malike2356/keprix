"""Upload and approval workflow for voice templates."""

from __future__ import annotations

import logging
from datetime import date

from keprix.voice_templates.audio_utils import AudioFormatError, validate_wav_format
from keprix.voice_templates.store import TemplateRecord, get_voice_template_store

logger = logging.getLogger(__name__)


async def submit_template(
    *,
    workspace_id: str,
    category_id: str,
    language_code: str,
    audio_bytes: bytes,
    transcript: str,
    transcript_english: str,
    recorded_by: str,
    recorded_at: date,
    dialect_note: str | None = None,
) -> TemplateRecord:
    store = get_voice_template_store()
    if store.get_category(category_id) is None:
        raise ValueError(f"Unknown category: {category_id}")
    duration = validate_wav_format(audio_bytes)
    audio_file_id = store.save_audio(audio_bytes, workspace_id=workspace_id)
    record = store.create_template(
        category_id=category_id,
        language_code=language_code,
        audio_file_id=audio_file_id,
        transcript=transcript.strip(),
        transcript_english=transcript_english.strip(),
        duration_seconds=duration,
        recorded_by=recorded_by,
        recorded_at=recorded_at,
        dialect_note=dialect_note,
        workspace_id=workspace_id,
        status="pending",
    )
    logger.info(
        "Voice template submitted workspace=%s category=%s language=%s id=%s",
        workspace_id,
        category_id,
        language_code,
        record.id,
    )
    return record


async def approve_template(
    template_id: str,
    *,
    approver_user_id: str,
    quality_rating: int,
) -> TemplateRecord | None:
    store = get_voice_template_store()
    return store.approve_template(
        template_id,
        approver_user_id=approver_user_id,
        quality_rating=quality_rating,
    )


async def reject_template(template_id: str, *, reason: str) -> TemplateRecord | None:
    store = get_voice_template_store()
    return store.reject_template(template_id, reason=reason)


def validate_upload_content_type(content_type: str | None, filename: str | None) -> None:
    name = (filename or "").lower()
    ctype = (content_type or "").lower()
    if not (name.endswith(".wav") or "wav" in ctype):
        raise AudioFormatError("Upload must be a WAV file")
