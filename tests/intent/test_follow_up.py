"""Tests for follow-up prompt generation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.backend.intent.follow_up import FollowUpGenerator
from keprix.backend.intent.schemas import IntentExtractionResult
from keprix.backend.intent.skill_loader import get_skill_loader
from keprix.backend.localization.schemas import TranslationResult


@pytest.mark.asyncio
async def test_follow_up_none_when_complete(intent_env) -> None:
    result = IntentExtractionResult(
        intent="greeting",
        confidence=0.9,
        original_language="en-GH",
        missing_required=[],
    )
    updated = await FollowUpGenerator().generate(result, "en-GH", "default")
    assert updated.follow_up_prompt is None


@pytest.mark.asyncio
async def test_follow_up_translated_to_user_language(intent_env) -> None:
    get_skill_loader().set_loaded_domains("ws-borehole", ["borehole_drilling"])
    result = IntentExtractionResult(
        intent="request_drilling_quote",
        confidence=0.88,
        original_language="ak-GH",
        domain="borehole_drilling",
        entities={"location_description": "near Tamale"},
        missing_required=["depth_target_metres"],
    )
    translation = TranslationResult(
        source_language="en",
        target_language="ak-GH",
        source_text="To give you a quote, I need: depth target metres. Please provide these.",
        translated_text="Fa depth target metres ma me na mma wo quote.",
        confidence=0.9,
        glossary_matches=[],
        warnings=[],
        provider="local",
    )
    with patch(
        "keprix.backend.localization.translation.translate_text",
        new=AsyncMock(return_value=translation),
    ):
        updated = await FollowUpGenerator().generate(result, "ak-GH", "ws-borehole")
    assert updated.follow_up_prompt == translation.translated_text
