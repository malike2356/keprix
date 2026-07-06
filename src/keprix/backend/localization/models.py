"""SQLAlchemy models for localization persistence (Prompt 27 / migration 010)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from keprix.database import Base, get_engine, get_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserLanguagePreferenceRow(Base):
    __tablename__ = "user_language_preferences"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_input_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_output_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_output_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    preferred_voice_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    bilingual_replies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LocalizationAuditRow(Base):
    __tablename__ = "localization_audit"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    translated_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcription_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    glossary_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    glossary_warnings: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LocalizationCorrectionRow(Base):
    __tablename__ = "localization_corrections"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    audit_record_id: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_id: Mapped[str] = mapped_column(Text, nullable=False)
    correction_type: Mapped[str] = mapped_column(Text, nullable=False)
    original_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(Text, nullable=False)
    target_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str] = mapped_column(Text, nullable=False, default="generic")
    submitted_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    reviewed_by_user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_to_glossary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    staged_for_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    training_sample_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class LocalizationTrainingSampleRow(Base):
    __tablename__ = "localization_training_samples"

    id: Mapped[str] = mapped_column(Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    correction_id: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(Text, nullable=False)
    target_language: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_audio_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, nullable=False, default="generic")
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    included_in_export_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def ensure_localization_tables() -> None:
    factory = get_session_factory()
    if factory is None:
        return
    engine = get_engine()
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                UserLanguagePreferenceRow.__table__,
                LocalizationAuditRow.__table__,
                LocalizationCorrectionRow.__table__,
                LocalizationTrainingSampleRow.__table__,
            ],
        )


def preference_row_to_dict(row: UserLanguagePreferenceRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "user_id": row.user_id,
        "preferred_input_language": row.preferred_input_language,
        "preferred_output_language": row.preferred_output_language,
        "voice_output_enabled": row.voice_output_enabled,
        "preferred_voice_id": row.preferred_voice_id,
        "bilingual_replies": row.bilingual_replies,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def audit_row_to_dict(row: LocalizationAuditRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "user_id": row.user_id,
        "channel": row.channel,
        "request_id": row.request_id,
        "input_type": row.input_type,
        "original_text": row.original_text,
        "translated_input": row.translated_input,
        "final_response": row.final_response,
        "detected_language": row.detected_language,
        "output_language": row.output_language,
        "detection_confidence": row.detection_confidence,
        "transcription_provider": row.transcription_provider,
        "translation_provider": row.translation_provider,
        "speech_provider": row.speech_provider,
        "glossary_id": row.glossary_id,
        "glossary_warnings": row.glossary_warnings or [],
        "human_review_required": row.human_review_required,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def correction_row_to_dict(row: LocalizationCorrectionRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "audit_record_id": row.audit_record_id,
        "workspace_id": row.workspace_id,
        "correction_type": row.correction_type,
        "original_value": row.original_value,
        "corrected_value": row.corrected_value,
        "source_language": row.source_language,
        "target_language": row.target_language,
        "domain": row.domain,
        "submitted_by_user_id": row.submitted_by_user_id,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        "status": row.status,
        "reviewed_by_user_id": row.reviewed_by_user_id,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "rejection_reason": row.rejection_reason,
        "applied_to_glossary": row.applied_to_glossary,
        "staged_for_training": row.staged_for_training,
        "training_sample_id": row.training_sample_id,
    }


def training_sample_row_to_dict(row: LocalizationTrainingSampleRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "correction_id": row.correction_id,
        "task_type": row.task_type,
        "source_language": row.source_language,
        "target_language": row.target_language,
        "source_text": row.source_text,
        "source_audio_file_id": row.source_audio_file_id,
        "target_text": row.target_text,
        "domain": row.domain,
        "quality_score": row.quality_score,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "included_in_export_at": row.included_in_export_at.isoformat() if row.included_in_export_at else None,
    }
