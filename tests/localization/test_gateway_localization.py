"""Gateway localization hook tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.backend.gateway.localization_hook import (
    apply_inbound_localization,
    apply_outbound_localization,
)
from keprix.backend.localization.schemas import InboundLocalizationResult
from keprix.gateway.config import Platform


@pytest.mark.asyncio
async def test_inbound_localization_skipped_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_LOCALIZATION_ENABLED", "false")
    text, ctx = await apply_inbound_localization(
        platform=Platform.TELEGRAM,
        user_id="u1",
        text="Akwaaba",
        voice_paths=[],
    )
    assert text is None
    assert ctx is None


@pytest.mark.asyncio
async def test_inbound_and_outbound_localization_for_telegram(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_LOCALIZATION_ENABLED", "true")
    inbound = InboundLocalizationResult(
        original_text="Me pɛ borehole",
        detected_language="ak-GH",
        workspace_language="en-GH",
        output_language="ak-GH",
        translated_input="I want a borehole",
        final_response="I want a borehole",
        translated_response="I want a borehole",
        detection_confidence=0.9,
        translation_confidence=0.88,
        human_review_required=False,
        glossary_warnings=[],
    )
    outbound = InboundLocalizationResult(
        original_text="Me pɛ borehole",
        detected_language="ak-GH",
        workspace_language="en-GH",
        output_language="ak-GH",
        translated_input="I want a borehole",
        final_response="Please share your GPS location.",
        translated_response="Fa wo GPS location ma me.",
        detection_confidence=0.9,
        translation_confidence=0.85,
        human_review_required=False,
        glossary_warnings=[],
        audio_url="/tmp/reply.wav",
        audit_id="audit-1",
    )
    with patch(
        "keprix.backend.gateway.localization_hook.process_inbound_message",
        new=AsyncMock(side_effect=[inbound, outbound]),
    ):
        agent_text, ctx = await apply_inbound_localization(
            platform=Platform.WHATSAPP,
            user_id="farmer-1",
            text="Me pɛ borehole",
            voice_paths=[],
        )
        assert agent_text == "I want a borehole"
        assert ctx is not None
        translated, audio_url, meta = await apply_outbound_localization(
            ctx,
            "Please share your GPS location.",
        )
    assert translated == "Fa wo GPS location ma me."
    assert audio_url == "/tmp/reply.wav"
    assert meta["audit_id"] == "audit-1"
