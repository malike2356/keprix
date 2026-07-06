"""API tests for workspace audio transcription routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limit import DEFAULT_RULES, RateLimitRule, reset_rate_limiter
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("KEPRIX_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    reset_rate_limits()
    reset_rate_limiter()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    return TestClient(create_app())


@pytest.fixture
def audio_client(api_client):
    login = api_client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    api_client.headers.update({"Authorization": f"Bearer {token}"})
    return api_client


def test_transcribe_requires_auth(api_client):
    response = api_client.post(
        "/api/audio/transcribe",
        json={"data_url": "data:audio/webm;base64,aGVsbG8=", "mime_type": "audio/webm"},
    )
    assert response.status_code == 401


def test_transcribe_rejects_invalid_data_url(audio_client):
    response = audio_client.post(
        "/api/audio/transcribe",
        json={"data_url": "not-a-data-url", "mime_type": "audio/webm"},
    )
    assert response.status_code == 400


def test_transcribe_when_stt_disabled(audio_client, monkeypatch):
    monkeypatch.setattr("keprix.api.audio_transcribe.stt_enabled", lambda: False)
    response = audio_client.post(
        "/api/audio/transcribe",
        json={"data_url": "data:audio/webm;base64,aGVsbG8=", "mime_type": "audio/webm"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Speech-to-text is disabled"


def test_transcribe_success(audio_client, monkeypatch):
    import tools.transcription_tools as transcription_tools

    captured: dict[str, str] = {}

    def fake_transcribe_audio(path: str):
        captured["path"] = path
        return {
            "success": True,
            "transcript": "hello from voice mode",
            "provider": "test",
        }

    monkeypatch.setattr(transcription_tools, "transcribe_audio", fake_transcribe_audio)

    response = audio_client.post(
        "/api/audio/transcribe",
        json={"data_url": "data:audio/webm;base64,aGVsbG8=", "mime_type": "audio/webm"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "transcript": "hello from voice mode",
        "provider": "test",
    }
    assert captured["path"].endswith(".webm")
    assert not Path(captured["path"]).exists()


def test_audio_status_endpoint(api_client, monkeypatch):
    monkeypatch.setattr("keprix.api.stt_config.stt_enabled", lambda: True)
    monkeypatch.setattr("keprix.api.stt_config.stt_provider", lambda: "local")
    monkeypatch.setattr("keprix.api.stt_config.max_recording_seconds", lambda: 120)

    response = api_client.get("/api/audio/status")
    assert response.status_code == 200
    assert response.json() == {
        "stt_enabled": True,
        "provider": "local",
        "max_recording_seconds": 120,
        "transcribe_path": "/api/audio/transcribe",
    }


def test_transcribe_rate_limited(audio_client, monkeypatch):
    import tools.transcription_tools as transcription_tools
    from keprix.security.rate_limit import RateLimiter

    monkeypatch.delenv("REDIS_URL", raising=False)
    memory_limiter = RateLimiter()
    memory_limiter._redis = None
    monkeypatch.setattr("keprix.security.rate_limit.get_rate_limiter", lambda: memory_limiter)

    monkeypatch.setattr(
        transcription_tools,
        "transcribe_audio",
        lambda path: {
            "success": True,
            "transcript": "ok",
            "provider": "test",
        },
    )
    monkeypatch.setitem(
        DEFAULT_RULES,
        "audio_transcribe",
        RateLimitRule("audio_transcribe", 2, 3600, "rl:audio-test"),
    )

    payload = {"data_url": "data:audio/webm;base64,aGVsbG8=", "mime_type": "audio/webm"}
    assert audio_client.post("/api/audio/transcribe", json=payload).status_code == 200
    assert audio_client.post("/api/audio/transcribe", json=payload).status_code == 200
    blocked = audio_client.post("/api/audio/transcribe", json=payload)
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"
