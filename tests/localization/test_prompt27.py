"""Prompt 27 integration tests."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, patch

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.gateway.language_middleware import InboundMessage, process_inbound_message
from keprix.backend.localization.config import LocalizationSettings
from keprix.backend.localization.detection import detect_language
from keprix.backend.localization.glossary import get_glossary_service
from keprix.backend.localization.preferences import get_preference_service
from keprix.backend.localization.slash import execute_language_slash
from keprix.backend.localization.translation import translate_text
from keprix.backend.playbook.localization import GHANA_BOREHOLE_PLAYBOOK


@pytest.mark.asyncio
async def test_detect_returns_language_code_and_confidence() -> None:
    result = await detect_language("Akwaaba, mepɛ borehole")
    assert result.language_code
    assert result.confidence >= 0.0
    assert result.provider


@pytest.mark.asyncio
async def test_user_preference_overrides_workspace_default(isolated_store) -> None:
    prefs = get_preference_service()
    await prefs.update("ws1", "user1", {"preferred_output_language": "tw-GH"})
    resolved = await prefs.resolve_output_language("ws1", "user1")
    assert resolved == "tw-GH"


@pytest.mark.asyncio
async def test_unknown_language_falls_back_with_warning() -> None:
    result = await detect_language("±±±±", allow_cloud=False)
    assert result.language_code == "en-GH"
    assert result.confidence <= 0.55


@pytest.mark.asyncio
async def test_glossary_protects_yield_test() -> None:
    glossary = get_glossary_service()
    ok = glossary.check_yield_test("Schedule a yield test for the borehole")
    bad = glossary.check_yield_test("This affects crop yield only")
    assert ok is True
    assert bad is False


@pytest.mark.asyncio
async def test_low_confidence_creates_human_review_audit(isolated_store) -> None:
    settings = LocalizationSettings(
        workspace_language="en-GH",
        default_output_language="ak-GH",
        human_review_below_confidence=0.95,
        allowed_cloud_processing=False,
    )
    result = await process_inbound_message(
        InboundMessage(
            workspace_id="ws-review",
            channel="webchat",
            user_id="u1",
            text="???",
            glossary_id="borehole_drilling_ghana_v1",
            domain="borehole_drilling",
            workspace_response="Please share your community name.",
        ),
        settings=settings,
    )
    assert result.human_review_required is True
    assert result.audit_id


@pytest.mark.asyncio
async def test_voice_output_skipped_when_channel_does_not_support_audio(isolated_store) -> None:
    await get_preference_service().update("ws-no-audio", "u1", {"voice_output_enabled": True})
    result = await process_inbound_message(
        InboundMessage(
            workspace_id="ws-no-audio",
            channel="webchat",
            user_id="u1",
            text="Hello",
            workspace_response="Reply text",
            channel_supports_audio=False,
        )
    )
    assert result.audio_url is None


@pytest.mark.asyncio
async def test_transcription_preserves_segments_and_language() -> None:
    from keprix.backend.localization.schemas import TranscriptionResult, TranscriptSegment
    from keprix.backend.localization.transcription import transcribe_audio

    fake = TranscriptionResult(
        language_code="ak-GH",
        transcript="Me pɛ borehole",
        confidence=0.91,
        segments=[
            TranscriptSegment(start=0.0, end=1.2, text="Me pɛ", confidence=0.9),
            TranscriptSegment(start=1.2, end=2.0, text="borehole", confidence=0.92),
        ],
        provider="whisper",
    )
    with patch(
        "keprix.backend.localization.transcription.select_transcription_provider",
        return_value="whisper",
    ), patch(
        "keprix.backend.localization.providers.whisper.WhisperProvider.transcribe",
        new=AsyncMock(return_value=fake),
    ):
        result = await transcribe_audio(b"audio-bytes", source_language="ak-GH")
    assert result.language_code == "ak-GH"
    assert len(result.segments) == 2
    assert result.segments[0].start == 0.0
    assert result.segments[1].end == 2.0


@pytest.mark.asyncio
async def test_voice_output_skipped_when_preference_disabled(isolated_store) -> None:
    await get_preference_service().update("ws-voice", "u1", {"voice_output_enabled": False})
    result = await process_inbound_message(
        InboundMessage(
            workspace_id="ws-voice",
            channel="telegram",
            user_id="u1",
            text="Hello",
            workspace_response="Reply text",
            channel_supports_audio=True,
        )
    )
    assert result.audio_url is None


@pytest.mark.asyncio
async def test_cloud_blocked_when_policy_disables_cloud() -> None:
    settings = LocalizationSettings(allowed_cloud_processing=False, offline_mode=True)
    with patch(
        "keprix.backend.localization.translation.select_translation_provider",
        return_value="cloud",
    ):
        result = await translate_text(
            workspace_id="ws",
            text="Hello",
            source_language="ak-GH",
            target_language="en",
        )
    assert "unavailable" in result.provider or result.warnings


@pytest.mark.asyncio
async def test_language_set_tw_gh() -> None:
    result = await execute_language_slash(
        workspace_id="ws-slash",
        user_id="u-slash",
        args=["set", "tw-GH"],
    )
    assert result.ok is True
    assert "tw-GH" in result.message


@pytest.mark.asyncio
async def test_language_set_sw_ke() -> None:
    result = await execute_language_slash(
        workspace_id="ws-slash",
        user_id="u-sw",
        args=["set", "sw-KE"],
    )
    assert result.ok is True


@pytest.mark.asyncio
async def test_language_set_yo_ng() -> None:
    result = await execute_language_slash(
        workspace_id="ws-slash",
        user_id="u-yo",
        args=["set", "yo-NG"],
    )
    assert result.ok is True


@pytest.mark.asyncio
async def test_language_voice_on() -> None:
    result = await execute_language_slash(
        workspace_id="ws-slash",
        user_id="u-voice",
        args=["voice", "on"],
    )
    assert result.ok is True
    assert result.payload["voice_output_enabled"] is True


@pytest.mark.asyncio
async def test_audit_records_provider_and_glossary_warnings(isolated_store) -> None:
    from keprix.backend.localization.schemas import TranslationResult

    fake = TranslationResult(
        source_language="ak-GH",
        target_language="en",
        source_text="test",
        translated_text="crop yield issue",
        confidence=0.4,
        glossary_matches=[],
        warnings=[],
        provider="cloud",
    )
    with patch(
        "keprix.backend.localization.translation.select_translation_provider",
        return_value="cloud",
    ), patch(
        "keprix.backend.localization.providers.cloud.CloudTranslationProvider.translate",
        new=AsyncMock(return_value=fake),
    ):
        result = await process_inbound_message(
            InboundMessage(
                workspace_id="ws-audit",
                channel="cli",
                user_id="u-audit",
                text="Me pɛ borehole",
                glossary_id="borehole_drilling_ghana_v1",
                domain="borehole_drilling",
                workspace_response="We need a yield test plan.",
            )
        )
    assert result.audit_id
    records = await isolated_store.list_audit("ws-audit")
    assert records[0]["glossary_id"] == "borehole_drilling_ghana_v1"


@pytest.mark.asyncio
async def test_original_input_preserved_in_review_mode(isolated_store) -> None:
    result = await process_inbound_message(
        InboundMessage(
            workspace_id="ws-orig",
            channel="webchat",
            user_id="u-orig",
            text="Original Twi phrase",
            workspace_response="English answer",
        )
    )
    records = await isolated_store.list_audit("ws-orig")
    assert records[0]["original_text"] == "Original Twi phrase"


@pytest.mark.asyncio
async def test_api_detect_translate_preferences(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    import keprix.backend.localization.store as store_module

    store_module._store = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        detect = await client.post("/api/localization/detect", json={"text": "Sawubona"})
        assert detect.status_code == 200
        translate = await client.post(
            "/api/localization/translate",
            json={"text": "Hello", "source_language": "en", "target_language": "en-GH"},
        )
        assert translate.status_code == 200
        prefs = await client.post(
            "/api/localization/preferences",
            params={"workspace_id": "default"},
            json={"preferred_output_language": "ak-GH", "voice_output_enabled": True},
        )
        assert prefs.status_code == 200
        assert prefs.json()["preferred_output_language"] == "ak-GH"


def test_borehole_playbook_metadata() -> None:
    assert GHANA_BOREHOLE_PLAYBOOK.glossary_id == "borehole_drilling_ghana_v1"
    assert GHANA_BOREHOLE_PLAYBOOK.supports_language("ak-GH")


def test_borehole_example_playbook_file() -> None:
    from pathlib import Path

    raw = yaml.safe_load(
        Path("examples/borehole-ghana/playbook.yaml").read_text(encoding="utf-8")
    )
    assert raw["domain"] == "borehole_drilling"
    assert "ak-GH" in raw["supported_input_languages"]
