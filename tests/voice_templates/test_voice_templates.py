"""Prompt 49 acceptance tests: voice template library, player, and API."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from keprix.voice_templates.routes import router as voice_templates_router
from keprix.voice_templates.audio_utils import concatenate_audio, make_test_wav, validate_wav_format
from keprix.voice_templates.library import VoiceTemplateLibrary, reset_template_library
from keprix.voice_templates.player import VoicePlayer, reset_voice_player
from keprix.voice_templates.store import get_voice_template_store, reset_voice_template_store
from keprix.voice_templates.approval import approve_template, submit_template


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(voice_templates_router)
    return test_app


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch, tmp_path):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUTH_ENABLED", "false")
    reset_voice_template_store()
    reset_template_library()
    reset_voice_player()
    yield
    reset_voice_template_store()
    reset_template_library()
    reset_voice_player()


@pytest.mark.asyncio
async def test_validate_wav_rejects_mp3_header():
    with pytest.raises(Exception):
        validate_wav_format(b"not a wav file")


def test_concatenate_audio_produces_longer_wav():
    a = make_test_wav(1.0)
    b = make_test_wav(1.0)
    combined = concatenate_audio(a, b, gap_ms=200)
    assert len(combined) > len(a) + len(b) - 100


@pytest.mark.asyncio
async def test_library_returns_workspace_template():
    wav = make_test_wav()
    record = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=wav,
        transcript="Maakye",
        transcript_english="Good morning",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    await approve_template(record.id, approver_user_id="admin", quality_rating=4)
    library = VoiceTemplateLibrary()
    found = await library.get_template("greeting", "ak-GH", "ws-1")
    assert found is not None
    assert found.transcript == "Maakye"


@pytest.mark.asyncio
async def test_library_falls_back_from_fante_to_twi():
    wav = make_test_wav()
    record = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=wav,
        transcript="Maakye",
        transcript_english="Good morning",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    await approve_template(record.id, approver_user_id="admin", quality_rating=4)
    library = VoiceTemplateLibrary()
    found = await library.get_template("greeting", "fan-GH", "ws-1")
    assert found is not None
    assert found.language_code == "ak-gh"


@pytest.mark.asyncio
async def test_library_returns_none_for_unsupported_language():
    library = VoiceTemplateLibrary()
    found = await library.get_template("greeting", "de-DE", "ws-1")
    assert found is None


@pytest.mark.asyncio
async def test_player_pure_template():
    await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=make_test_wav(),
        transcript="Maakye",
        transcript_english="Good morning",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    store = get_voice_template_store()
    pending = store.list_templates(status="pending")[0]
    await approve_template(pending.id, approver_user_id="admin", quality_rating=5)
    player = VoicePlayer()
    result = await player.assemble_response(
        "greeting",
        "ak-GH",
        None,
        "Hello",
        "ws-1",
    )
    assert result.method == "template"
    assert result.audio_url is not None
    assert result.template_id is not None


@pytest.mark.asyncio
async def test_player_hybrid_when_tts_available():
    store = get_voice_template_store()
    store.register_category(
        __import__("keprix.voice_templates.schemas", fromlist=["CategoryCreate"]).CategoryCreate(
            id="quote_ready",
            label="Quote ready",
            domain="borehole_drilling",
            is_dynamic=True,
            dynamic_placeholder="{price}",
        )
    )
    record = await submit_template(
        workspace_id="ws-1",
        category_id="quote_ready",
        language_code="ak-GH",
        audio_bytes=make_test_wav(),
        transcript="Wo quote asie.",
        transcript_english="Your quote is ready.",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    await approve_template(record.id, approver_user_id="admin", quality_rating=5)
    fake_wav = make_test_wav(0.5)
    with patch("keprix.voice_templates.player.synthesize_to_wav", return_value=fake_wav):
        with patch("keprix.voice_templates.tts_bridge.supports_tts", return_value=True):
            player = VoicePlayer()
            result = await player.assemble_response(
                "quote_ready",
                "ak-GH",
                "GHS 4,500",
                "Your quote is ready: GHS 4,500",
                "ws-1",
            )
    assert result.method == "template_tts_hybrid"
    assert "GHS 4,500" in result.transcript


@pytest.mark.asyncio
async def test_player_text_only_when_no_template_or_tts():
    player = VoicePlayer()
    with patch("keprix.voice_templates.player.supports_tts", return_value=False):
        result = await player.assemble_response(
            "greeting",
            "dag-GH",
            None,
            "Hello",
            "ws-1",
        )
    assert result.method == "text_only"
    assert result.audio_url is None


@pytest.mark.asyncio
async def test_approve_archives_previous_template():
    wav = make_test_wav()
    first = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=wav,
        transcript="First",
        transcript_english="First",
        recorded_by="A",
        recorded_at=date(2026, 1, 1),
    )
    second = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=wav,
        transcript="Second",
        transcript_english="Second",
        recorded_by="B",
        recorded_at=date(2026, 1, 2),
    )
    await approve_template(first.id, approver_user_id="admin", quality_rating=4)
    await approve_template(second.id, approver_user_id="admin", quality_rating=5)
    store = get_voice_template_store()
    assert store.get_template(first.id).status == "archived"
    assert store.get_template(second.id).status == "approved"


@pytest.mark.asyncio
async def test_play_count_increments_on_template_serve():
    record = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=make_test_wav(),
        transcript="Maakye",
        transcript_english="Good morning",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    await approve_template(record.id, approver_user_id="admin", quality_rating=5)
    player = VoicePlayer()
    await player.assemble_response("greeting", "ak-GH", None, "Hello", "ws-1")
    updated = get_voice_template_store().get_template(record.id)
    assert updated is not None
    assert updated.play_count == 1


@pytest.mark.asyncio
async def test_api_upload_rejects_non_wav(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/voice-templates",
            data={
                "category_id": "greeting",
                "language_code": "ak-GH",
                "transcript": "Hi",
                "transcript_english": "Hi",
                "recorded_by": "Tester",
                "recorded_at": "2026-01-01",
            },
            files={"audio_file": ("clip.mp3", b"fake", "audio/mpeg")},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_upload_rejects_long_wav(app):
    long_wav = make_test_wav(31.0)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/voice-templates",
            data={
                "category_id": "greeting",
                "language_code": "ak-GH",
                "transcript": "Hi",
                "transcript_english": "Hi",
                "recorded_by": "Tester",
                "recorded_at": "2026-01-01",
            },
            files={"audio_file": ("clip.wav", long_wav, "audio/wav")},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_api_upload_and_assemble_template(app):
    wav = make_test_wav()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upload = await client.post(
            "/api/voice-templates",
            data={
                "category_id": "greeting",
                "language_code": "ak-GH",
                "transcript": "Maakye",
                "transcript_english": "Good morning",
                "recorded_by": "Tester",
                "recorded_at": "2026-01-01",
                "workspace_id": "ws-1",
            },
            files={"audio_file": ("clip.wav", wav, "audio/wav")},
        )
        assert upload.status_code == 201
        template_id = upload.json()["template_id"]
        approve = await client.post(
            f"/api/voice-templates/{template_id}/approve",
            json={"quality_rating": 5},
        )
        assert approve.status_code == 200
        assembled = await client.post(
            "/api/voice-templates/assemble",
            json={
                "category_id": "greeting",
                "language_code": "ak-GH",
                "full_text_fallback": "Hello",
                "workspace_id": "ws-1",
            },
        )
    assert assembled.status_code == 200
    data = assembled.json()
    assert data["method"] == "template"
    assert data["audio_url"] == f"/api/voice-templates/{template_id}/audio"


@pytest.mark.asyncio
async def test_api_coverage_report(app):
    record = await submit_template(
        workspace_id="ws-1",
        category_id="greeting",
        language_code="ak-GH",
        audio_bytes=make_test_wav(),
        transcript="Maakye",
        transcript_english="Good morning",
        recorded_by="Speaker",
        recorded_at=date(2026, 1, 1),
    )
    await approve_template(record.id, approver_user_id="admin", quality_rating=5)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/voice-templates/coverage")
    assert response.status_code == 200
    langs = response.json()["languages"]
    assert "ak-gh" in langs
    assert langs["ak-gh"]["covered_categories"] >= 1
