"""Inbound message localization pipeline (Prompt 27 runtime flow)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from keprix.backend.localization.audit import get_audit_service
from keprix.backend.localization.confidence import should_require_human_review
from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.detection import detect_language
from keprix.backend.localization.preferences import get_preference_service
from keprix.backend.localization.schemas import InboundLocalizationResult, LocalizationAuditRecord
from keprix.backend.localization.speech import synthesize_speech
from keprix.backend.localization.transcription import transcribe_audio
from keprix.backend.localization.translation import translate_text


@dataclass
class InboundMessage:
    workspace_id: str
    channel: str
    user_id: str | None
    text: str | None = None
    audio_bytes: bytes | None = None
    request_id: str | None = None
    glossary_id: str | None = None
    domain: str | None = None
    channel_supports_audio: bool = True
    workspace_response: str | None = None
    conversation_history: list[dict[str, Any]] | None = None


async def process_inbound_message(
    message: InboundMessage,
    *,
    settings: LocalizationSettings | None = None,
    write_audit: bool = True,
    inbound_state: InboundLocalizationResult | None = None,
) -> InboundLocalizationResult:
    settings = settings or LocalizationSettings.from_env(message.workspace_id)
    request_id = message.request_id or str(uuid.uuid4())
    warnings: list[str] = []
    intent_payload: dict[str, Any] | None = None
    follow_up_prompt: str | None = None
    requires_follow_up = False

    if inbound_state is not None:
        original_text = inbound_state.original_text
        detected_language = inbound_state.detected_language
        detection_confidence = inbound_state.detection_confidence
        translated_input = inbound_state.translated_input
        translation_confidence = inbound_state.translation_confidence
        glossary_warnings = list(inbound_state.glossary_warnings)
        transcription_provider: str | None = None
        translation_provider: str | None = None
        output_language = inbound_state.output_language
        intent_payload = inbound_state.intent
        follow_up_prompt = inbound_state.follow_up_prompt
        requires_follow_up = inbound_state.requires_follow_up
    else:
        original_text = message.text or ""
        detected_language = settings.workspace_language
        detection_confidence = 1.0
        transcription_provider = None
        translation_provider = None
        glossary_warnings: list[str] = []

        if message.audio_bytes:
            transcription = await transcribe_audio(
                message.audio_bytes,
                target_language=settings.workspace_language,
                settings=settings,
            )
            original_text = transcription.transcript
            detected_language = transcription.language_code or detected_language
            detection_confidence = transcription.confidence
            transcription_provider = transcription.provider
            if not original_text:
                warnings.append("Transcription returned empty text")

        if original_text:
            detection = await detect_language(
                original_text,
                allow_cloud=settings.allowed_cloud_processing and not settings.offline_mode,
            )
            detected_language = detection.language_code
            detection_confidence = detection.confidence

        output_language = await get_preference_service().resolve_output_language(
            message.workspace_id,
            message.user_id,
            settings=settings,
        )

        translated_input = original_text
        translation_confidence = 1.0

        if original_text and detected_language.split("-")[0] != settings.workspace_language.split("-")[0]:
            inbound = await translate_text(
                workspace_id=message.workspace_id,
                text=original_text,
                source_language=detected_language,
                target_language=settings.workspace_language,
                glossary_id=message.glossary_id,
                user_id=message.user_id,
            )
            translated_input = inbound.translated_text
            translation_confidence = inbound.confidence
            translation_provider = inbound.provider
            glossary_warnings.extend(inbound.warnings)

    if (
        intent_payload is None
        and settings.intent_extraction_enabled
        and translated_input
        and not message.workspace_response
    ):
        from keprix.backend.intent.engine import get_intent_engine

        intent_result = await get_intent_engine().extract(
            translated_text=translated_input,
            original_text=original_text,
            source_language=detected_language,
            workspace_id=message.workspace_id,
            conversation_history=message.conversation_history,
        )
        intent_payload = intent_result.model_dump()
        follow_up_prompt = intent_result.follow_up_prompt
        if intent_result.follow_up_prompt and intent_result.confidence > 0.6:
            requires_follow_up = True

    final_response = message.workspace_response or translated_input
    translated_response = final_response
    speech_provider: str | None = None
    audio_url: str | None = None

    if final_response and output_language.split("-")[0] != settings.workspace_language.split("-")[0]:
        outbound = await translate_text(
            workspace_id=message.workspace_id,
            text=final_response,
            source_language=settings.workspace_language,
            target_language=output_language,
            glossary_id=message.glossary_id,
            user_id=message.user_id,
        )
        translated_response = outbound.translated_text
        translation_confidence = min(
            inbound_state.translation_confidence if inbound_state else translation_confidence,
            outbound.confidence,
        )
        glossary_warnings.extend(outbound.warnings)
        if translation_provider is None:
            translation_provider = outbound.provider

    human_review = should_require_human_review(
        settings=settings,
        detection_confidence=detection_confidence,
        translation_confidence=translation_confidence,
        glossary_warnings=glossary_warnings,
        domain=message.domain,
    )

    if message.workspace_response:
        speech = await synthesize_speech(
            translated_response,
            output_language,
            workspace_id=message.workspace_id,
            user_id=message.user_id,
            channel_supports_audio=message.channel_supports_audio,
            settings=settings,
        )
        if speech is not None:
            audio_url = speech.audio_url or None
            speech_provider = speech.provider

    audit_id: str | None = None
    if write_audit or message.workspace_response:
        audit = await get_audit_service().write(
            LocalizationAuditRecord(
                workspace_id=message.workspace_id,
                user_id=message.user_id,
                channel=message.channel,
                request_id=request_id,
                input_type="audio" if message.audio_bytes else "text",
                original_text=original_text,
                translated_input=translated_input,
                final_response=translated_response if message.workspace_response else None,
                detected_language=detected_language,
                output_language=output_language,
                detection_confidence=detection_confidence,
                transcription_provider=transcription_provider,
                translation_provider=translation_provider,
                speech_provider=speech_provider,
                glossary_id=message.glossary_id,
                glossary_warnings=glossary_warnings,
                human_review_required=human_review,
            )
        )
        audit_id = audit.get("id")

    return InboundLocalizationResult(
        original_text=original_text,
        detected_language=detected_language,
        workspace_language=settings.workspace_language,
        output_language=output_language,
        translated_input=translated_input,
        final_response=final_response,
        translated_response=translated_response,
        detection_confidence=detection_confidence,
        translation_confidence=translation_confidence,
        human_review_required=human_review,
        glossary_warnings=glossary_warnings,
        audio_url=audio_url,
        audit_id=audit_id,
        warnings=warnings,
        intent=intent_payload,
        follow_up_prompt=follow_up_prompt,
        requires_follow_up=requires_follow_up,
    )
