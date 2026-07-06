"""Tests for SeamlessM4T provider adapter."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest

from keprix.backend.localization.providers.base import LanguagePairUnsupported
from keprix.backend.localization.providers.seamless_m4t import (
    SeamlessM4TProvider,
    protect_terms,
    restore_terms,
)


def test_protect_and_restore_terms_round_trip() -> None:
    text = "We need a borehole pump at the site."
    protected, restore_map = protect_terms(text, ["borehole"])
    assert "borehole" not in protected.lower()
    assert "borehole" in restore_terms(protected, restore_map).lower()


@pytest.mark.asyncio
async def test_translate_ewe_preserves_terms() -> None:
    provider = SeamlessM4TProvider()
    with patch.object(provider, "_call", new=AsyncMock(return_value={"text": "We need __TERM_0__", "confidence": 0.91})):
        result = await provider.translate(
            "Míele borehole",
            source_language="ee-GH",
            target_language="en",
            preserve_terms=["borehole"],
        )
    assert result.provider == "seamless_m4t"
    assert result.translated_text == "We need borehole"
    assert result.confidence == 0.91


@pytest.mark.asyncio
async def test_transcribe_twi_audio() -> None:
    provider = SeamlessM4TProvider()
    audio = b"fake-audio-bytes"
    with patch.object(
        provider,
        "_call",
        new=AsyncMock(
            return_value={
                "text": "Hello in English",
                "detected_language": "twi",
                "confidence": 0.87,
                "segments": [{"start": 0.0, "end": 1.2, "text": "Hello", "confidence": 0.87}],
            }
        ),
    ):
        result = await provider.transcribe(audio, source_language="ak-GH", target_language="en")
    assert result.provider == "seamless_m4t"
    assert result.transcript == "Hello in English"
    assert result.language_code == "ak-GH"
    assert len(result.segments) == 1


@pytest.mark.asyncio
async def test_synthesize_speech_returns_audio_url() -> None:
    provider = SeamlessM4TProvider()
    audio_b64 = base64.b64encode(b"RIFFfake").decode("ascii")
    with patch.object(
        provider,
        "_call",
        new=AsyncMock(return_value={"text": "transcript", "audio_base64": audio_b64}),
    ):
        result = await provider.synthesize_speech("Akwaaba", language="ak-GH")
    assert result.provider == "seamless_m4t"
    assert result.audio_url.startswith("file://")
    assert result.transcript == "Akwaaba"


@pytest.mark.asyncio
async def test_unsupported_language_pair_raises() -> None:
    provider = SeamlessM4TProvider()
    with pytest.raises(LanguagePairUnsupported):
        await provider.translate("text", source_language="xx-XX", target_language="en")


@pytest.mark.asyncio
async def test_health_check_sidecar_ok() -> None:
    provider = SeamlessM4TProvider()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("keprix.backend.localization.providers.seamless_m4t.httpx.AsyncClient", return_value=mock_client):
        health = await provider.health_check()
    assert health["status"] == "ok"
    assert health["provider"] == "seamless_m4t"
