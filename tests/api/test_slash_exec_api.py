"""API tests for TUI slash exec and completion (Prompt 205)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def slash_api_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_slash_exec_status(slash_api_client) -> None:
    response = slash_api_client.post(
        "/api/slash/exec",
        json={"command": "status", "session_id": "sess-1", "platform": "tui"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert isinstance(payload.get("output"), str)


def test_slash_complete_memory_prefix_sorted(slash_api_client) -> None:
    response = slash_api_client.post(
        "/api/slash/complete",
        json={"prefix": "/mem", "session_id": "sess-1"},
    )
    assert response.status_code == 200
    candidates = response.json().get("candidates") or []
    assert candidates == sorted(candidates)
    assert any("memory" in item.lower() for item in candidates)


def test_command_dispatch_unknown_returns_404(slash_api_client) -> None:
    response = slash_api_client.post(
        "/api/command/dispatch",
        json={"name": "zzz", "arg": "", "session_id": "sess-1"},
    )
    assert response.status_code == 404


def test_command_dispatch_queue_requires_arg(slash_api_client) -> None:
    response = slash_api_client.post(
        "/api/command/dispatch",
        json={"name": "queue", "arg": "", "session_id": "sess-1"},
    )
    assert response.status_code == 400
