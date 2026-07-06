"""Telegram/WhatsApp gateway hooks for Prompt 27 localization middleware."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.backend.gateway.language_middleware import InboundMessage, process_inbound_message
from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.schemas import InboundLocalizationResult
from keprix.gateway.config import Platform


LOCALIZATION_PLATFORMS = frozenset(
    {
        Platform.TELEGRAM,
        Platform.WHATSAPP,
        Platform.WHATSAPP_CLOUD,
    }
)


@dataclass
class GatewayLocalizationContext:
    request_id: str
    workspace_id: str
    channel: str
    user_id: str | None
    original_text: str
    detected_language: str
    output_language: str
    translated_input: str
    glossary_id: str | None
    domain: str | None
    channel_supports_audio: bool
    inbound_result: InboundLocalizationResult


def gateway_workspace_id() -> str:
    return os.environ.get("KEPRIX_WORKSPACE_ID", "default")


def gateway_glossary_id() -> str | None:
    value = os.environ.get("KEPRIX_LOCALIZATION_GLOSSARY_ID", "").strip()
    return value or None


def gateway_domain() -> str | None:
    value = os.environ.get("KEPRIX_LOCALIZATION_DOMAIN", "").strip()
    return value or None


def should_apply_gateway_localization(platform: Platform | None) -> bool:
    if platform is None or platform not in LOCALIZATION_PLATFORMS:
        return False
    return LocalizationSettings.from_env(gateway_workspace_id()).enabled


def read_audio_file(path: str) -> bytes | None:
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


async def apply_inbound_localization(
    *,
    platform: Platform,
    user_id: str | None,
    text: str,
    voice_paths: list[str],
) -> tuple[str | None, GatewayLocalizationContext | None]:
    """Detect/transcribe/translate inbound user text for the agent."""
    if not should_apply_gateway_localization(platform):
        return None, None

    settings = LocalizationSettings.from_env(gateway_workspace_id())
    audio_bytes = read_audio_file(voice_paths[0]) if voice_paths else None
    request_id = str(uuid.uuid4())
    channel = platform.value

    result = await process_inbound_message(
        InboundMessage(
            workspace_id=gateway_workspace_id(),
            channel=channel,
            user_id=user_id,
            text=text if not audio_bytes else (text or None),
            audio_bytes=audio_bytes,
            request_id=request_id,
            glossary_id=gateway_glossary_id(),
            domain=gateway_domain(),
            channel_supports_audio=True,
        ),
        settings=settings,
        write_audit=False,
    )

    agent_text = result.translated_input or result.original_text or text
    ctx = GatewayLocalizationContext(
        request_id=request_id,
        workspace_id=gateway_workspace_id(),
        channel=channel,
        user_id=user_id,
        original_text=result.original_text or text,
        detected_language=result.detected_language,
        output_language=result.output_language,
        translated_input=agent_text,
        glossary_id=gateway_glossary_id(),
        domain=gateway_domain(),
        channel_supports_audio=True,
        inbound_result=result,
    )
    return agent_text, ctx


async def apply_outbound_localization(
    ctx: GatewayLocalizationContext,
    response_text: str,
) -> tuple[str, str | None, dict[str, Any] | None]:
    """Translate agent response and optionally synthesize voice output."""
    settings = LocalizationSettings.from_env(ctx.workspace_id)
    result = await process_inbound_message(
        InboundMessage(
            workspace_id=ctx.workspace_id,
            channel=ctx.channel,
            user_id=ctx.user_id,
            text=ctx.original_text,
            request_id=ctx.request_id,
            glossary_id=ctx.glossary_id,
            domain=ctx.domain,
            workspace_response=response_text,
            channel_supports_audio=ctx.channel_supports_audio,
        ),
        settings=settings,
        inbound_state=ctx.inbound_result,
    )
    return (
        result.translated_response or response_text,
        result.audio_url,
        {"audit_id": result.audit_id, "human_review_required": result.human_review_required},
    )
