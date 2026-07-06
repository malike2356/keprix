"""End-to-end API flow for workspace voice transcription."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limit import reset_rate_limiter
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def voice_e2e_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("KEPRIX_ADMIN_EMAIL", raising=False)
    reset_rate_limits()
    reset_rate_limiter()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_web_voice_transcribe_e2e(voice_e2e_client, monkeypatch):
    import tools.transcription_tools as transcription_tools

    monkeypatch.setattr(
        transcription_tools,
        "transcribe_audio",
        lambda path: {
            "success": True,
            "transcript": "what is DCB0129",
            "provider": "local",
        },
    )

    response = voice_e2e_client.post(
        "/api/audio/transcribe",
        json={"data_url": "data:audio/webm;base64,aGVsbG8=", "mime_type": "audio/webm"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["transcript"] == "what is DCB0129"
    assert body["provider"] == "local"
