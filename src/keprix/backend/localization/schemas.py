"""Typed models for all localization operations (Prompt 27 language contract)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LanguageCandidate:
    language_code: str
    language_name: str
    confidence: float


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: Optional[float] = None


@dataclass
class TranscriptionResult:
    language_code: str
    transcript: str
    confidence: float
    segments: list[TranscriptSegment]
    provider: str


@dataclass
class TranslationRequest:
    workspace_id: str
    target_language: str
    text: str
    source_language: str | None = None
    domain: str | None = None
    glossary_id: str | None = None
    preserve_terms: list[str] = field(default_factory=list)
    user_id: str | None = None


@dataclass
class TranslationResult:
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    confidence: float
    glossary_matches: list[str]
    warnings: list[str]
    provider: str


@dataclass
class SpeechSynthesisResult:
    language_code: str
    voice_id: str
    audio_url: str
    transcript: str
    provider: str


@dataclass
class LanguageDetectionResult:
    language_code: str
    language_name: str
    confidence: float
    provider: str
    script: Optional[str] = None
    region: Optional[str] = None
    alternatives: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LocalizationAuditRecord:
    workspace_id: str
    channel: str
    request_id: str
    input_type: str
    user_id: str | None = None
    original_text: str | None = None
    translated_input: str | None = None
    final_response: str | None = None
    detected_language: str | None = None
    output_language: str | None = None
    detection_confidence: float | None = None
    transcription_provider: str | None = None
    translation_provider: str | None = None
    speech_provider: str | None = None
    glossary_id: str | None = None
    glossary_warnings: list[str] = field(default_factory=list)
    human_review_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "request_id": self.request_id,
            "input_type": self.input_type,
            "original_text": self.original_text,
            "translated_input": self.translated_input,
            "final_response": self.final_response,
            "detected_language": self.detected_language,
            "output_language": self.output_language,
            "detection_confidence": self.detection_confidence,
            "transcription_provider": self.transcription_provider,
            "translation_provider": self.translation_provider,
            "speech_provider": self.speech_provider,
            "glossary_id": self.glossary_id,
            "glossary_warnings": self.glossary_warnings,
            "human_review_required": self.human_review_required,
            "metadata": self.metadata,
        }


@dataclass
class InboundLocalizationResult:
    original_text: str
    detected_language: str
    workspace_language: str
    output_language: str
    translated_input: str
    final_response: str
    translated_response: str
    detection_confidence: float
    translation_confidence: float
    human_review_required: bool
    glossary_warnings: list[str]
    audio_url: str | None = None
    audit_id: str | None = None
    warnings: list[str] = field(default_factory=list)
    intent: dict[str, Any] | None = None
    follow_up_prompt: str | None = None
    requires_follow_up: bool = False

