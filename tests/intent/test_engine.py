"""Tests for intent extraction engine (Prompt 48 acceptance)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from keprix.backend.intent.engine import IntentExtractionEngine, get_intent_engine
from keprix.backend.intent.skill_loader import get_skill_loader
from keprix.backend.gateway.language_middleware import InboundMessage, process_inbound_message
from keprix.backend.localization.config import LocalizationSettings


@pytest.fixture
def borehole_workspace(intent_env):
    get_skill_loader().set_loaded_domains("ws-borehole", ["borehole_drilling"])
    return "ws-borehole"


@pytest.mark.asyncio
async def test_borehole_quote_extracts_location_and_missing_depth(borehole_workspace) -> None:
    result = await get_intent_engine().extract(
        translated_text="I want a borehole quote near Tamale",
        original_text="Me pe borehole quote wɔ Tamale",
        source_language="ak-GH",
        workspace_id=borehole_workspace,
    )
    assert result.intent == "request_drilling_quote"
    assert result.entities.get("location_description") == "near Tamale"
    assert "depth_target_metres" in result.missing_required
    assert result.follow_up_prompt is not None


@pytest.mark.asyncio
async def test_greeting_in_akan(borehole_workspace) -> None:
    result = await get_intent_engine().extract(
        translated_text="Good morning",
        original_text="Mema wo akye",
        source_language="ak-GH",
        workspace_id=borehole_workspace,
    )
    assert result.intent == "greeting"
    assert result.confidence >= 0.8


@pytest.mark.asyncio
async def test_cancel_in_akan(borehole_workspace) -> None:
    result = await get_intent_engine().extract(
        translated_text="No",
        original_text="Daabi",
        source_language="ak-GH",
        workspace_id=borehole_workspace,
    )
    assert result.intent == "cancel"


@pytest.mark.asyncio
async def test_noise_falls_back(borehole_workspace) -> None:
    result = await get_intent_engine().extract(
        translated_text="gjhsadfkjhsad",
        original_text="gjhsadfkjhsad",
        source_language="en-GH",
        workspace_id=borehole_workspace,
    )
    assert result.intent == "fallback"
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_complete_entities_have_no_follow_up(borehole_workspace) -> None:
    result = await get_intent_engine().extract(
        translated_text="Quote for borehole near Tamale at 60 metres depth",
        original_text="Quote borehole Tamale 60m",
        source_language="en-GH",
        workspace_id=borehole_workspace,
    )
    assert result.intent == "request_drilling_quote"
    assert "depth_target_metres" not in result.missing_required
    assert result.follow_up_prompt is None


@pytest.mark.asyncio
async def test_conversation_history_in_user_message(borehole_workspace) -> None:
    engine = IntentExtractionEngine()
    message = engine.build_user_message(
        "I want a quote",
        "Me pe quote",
        "ak-GH",
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "Need borehole"},
        ],
    )
    assert "Recent conversation:" in message
    assert "Need borehole" in message


@pytest.mark.asyncio
async def test_extract_completes_under_two_seconds(borehole_workspace) -> None:
    started = time.monotonic()
    await get_intent_engine().extract(
        translated_text="I want a borehole quote near Tamale",
        original_text="Mema wo akye",
        source_language="ak-GH",
        workspace_id=borehole_workspace,
    )
    assert time.monotonic() - started < 2.0


@pytest.mark.asyncio
async def test_middleware_attaches_intent(borehole_workspace) -> None:
    settings = LocalizationSettings(
        workspace_language="en-GH",
        intent_extraction_enabled=True,
    )
    get_skill_loader().set_loaded_domains(borehole_workspace, ["borehole_drilling"])
    with patch(
        "keprix.backend.gateway.language_middleware.detect_language",
        new=AsyncMock(
            return_value=type(
                "Det",
                (),
                {"language_code": "ak-GH", "confidence": 0.9},
            )()
        ),
    ), patch(
        "keprix.backend.gateway.language_middleware.translate_text",
        new=AsyncMock(
            return_value=type(
                "Tr",
                (),
                {
                    "translated_text": "I want a borehole quote near Tamale",
                    "confidence": 0.9,
                    "warnings": [],
                    "provider": "local",
                },
            )()
        ),
    ), patch(
        "keprix.backend.gateway.language_middleware.get_preference_service",
    ) as pref_mock:
        pref_mock.return_value.resolve_output_language = AsyncMock(return_value="ak-GH")
        result = await process_inbound_message(
            InboundMessage(
                workspace_id=borehole_workspace,
                channel="web",
                user_id="user-1",
                text="Me pe borehole quote wɔ Tamale",
            ),
            settings=settings,
            write_audit=False,
        )
    assert result.intent is not None
    assert result.intent["intent"] == "request_drilling_quote"
