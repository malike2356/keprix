"""Tests for NLLB-200 provider adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.backend.localization.providers.base import LanguagePairUnsupported
from keprix.backend.localization.providers.nllb_200 import NLLB200Provider


@pytest.mark.asyncio
async def test_translate_dagbani_to_english() -> None:
    provider = NLLB200Provider()
    with patch.object(
        provider,
        "_call",
        new=AsyncMock(return_value={"translation": "Good morning", "score": 0.86}),
    ):
        result = await provider.translate(
            "Antire",
            source_language="dag-GH",
            target_language="en",
        )
    assert result.provider == "nllb_200"
    assert result.translated_text == "Good morning"
    assert result.confidence == 0.86


@pytest.mark.asyncio
async def test_batch_translate_returns_ten_results() -> None:
    provider = NLLB200Provider()
    texts = [f"sentence {index}" for index in range(10)]
    translations = [{"translation": f"translated {index}", "score": 0.8} for index in range(10)]
    with patch.object(
        provider,
        "_call_batch",
        new=AsyncMock(return_value={"translations": translations}),
    ):
        results = await provider.batch_translate(texts, source_language="nzi-GH", target_language="en")
    assert len(results) == 10
    assert all(item.provider == "nllb_200" for item in results)
    assert results[0].translated_text == "translated 0"


@pytest.mark.asyncio
async def test_unsupported_language_raises() -> None:
    provider = NLLB200Provider()
    with pytest.raises(LanguagePairUnsupported):
        await provider.translate("text", source_language="xx-XX", target_language="en")


@pytest.mark.asyncio
async def test_translate_preserves_terms() -> None:
    provider = NLLB200Provider()
    with patch.object(
        provider,
        "_call",
        new=AsyncMock(return_value={"translation": "Install __TERM_0__ here", "score": 0.9}),
    ):
        result = await provider.translate(
            "Fa borehole no",
            source_language="ak-GH",
            target_language="en",
            preserve_terms=["borehole"],
        )
    assert "borehole" in result.translated_text
