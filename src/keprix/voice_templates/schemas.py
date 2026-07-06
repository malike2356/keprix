"""Pydantic models for voice templates."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


TemplateStatus = Literal["pending", "approved", "rejected", "archived"]
AssemblyMethod = Literal["template", "template_tts_hybrid", "tts", "text_only"]


class CategoryCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    label: str
    description: str | None = None
    domain: str = "generic"
    is_dynamic: bool = False
    dynamic_placeholder: str | None = None
    sort_order: int = 0


class CategoryOut(BaseModel):
    id: str
    label: str
    description: str | None = None
    domain: str
    is_dynamic: bool
    dynamic_placeholder: str | None = None
    sort_order: int


class VoiceTemplateOut(BaseModel):
    id: str
    category_id: str
    language_code: str
    dialect_note: str | None = None
    audio_file_id: str
    transcript: str
    transcript_english: str
    duration_seconds: float
    recorded_by: str | None = None
    recorded_at: date | None = None
    quality_rating: int | None = None
    status: TemplateStatus
    approved_by_user_id: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    play_count: int
    workspace_id: str | None = None
    created_at: datetime
    audio_url: str | None = None


class ApproveBody(BaseModel):
    quality_rating: int = Field(..., ge=1, le=5)


class RejectBody(BaseModel):
    reason: str = Field(..., min_length=1)


class AssembleBody(BaseModel):
    category_id: str
    language_code: str
    dynamic_text: str | None = None
    full_text_fallback: str
    workspace_id: str | None = None


class VoiceResponseAssemblyOut(BaseModel):
    audio_url: str | None = None
    transcript: str
    method: AssemblyMethod
    template_id: str | None = None


class CoverageLanguageOut(BaseModel):
    language_code: str
    total_categories: int
    covered_categories: int
    coverage_pct: float


class LanguageFallbackUpdate(BaseModel):
    language_code: str
    fallback_language_code: str


class SubmitTemplateMeta(BaseModel):
    category_id: str
    language_code: str
    transcript: str
    transcript_english: str
    recorded_by: str
    recorded_at: date
    dialect_note: str | None = None
    workspace_id: str | None = None

    @field_validator("language_code")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip()


class TemplateListQuery(BaseModel):
    language_code: str | None = None
    category_id: str | None = None
    status: TemplateStatus | None = None
    workspace_id: str | None = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)
