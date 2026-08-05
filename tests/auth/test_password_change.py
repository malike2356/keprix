"""Tests for logged-in password change."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits

AUDIT_EVENTS: list[tuple[str, dict]] = []


async def _capture_audit(event_type: str, **kwargs):
    AUDIT_EVENTS.append((event_type, kwargs))


@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    AUDIT_EVENTS.clear()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.password_routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.password_routes.audit_log", _capture_audit)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, auth, token


def test_change_password_success(auth_client):
    client, auth, token = auth_client
    other_token = auth.create_session("alice")

    response = client.post(
        "/api/auth/me/password",
        json={"current_password": "alice-pass", "new_password": "new-secure-pass"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    assert auth.validate_token(other_token) is None
    assert auth.validate_token(token) is not None

    old_login = client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    assert old_login.status_code == 401

    client.headers.pop("Authorization", None)
    new_login = client.post("/api/auth/login", json={"username": "alice", "password": "new-secure-pass"})
    assert new_login.status_code == 200

    assert any(event[0] == "password_changed" for event in AUDIT_EVENTS)


def test_change_password_wrong_current_returns_401(auth_client):
    client, _auth, _token = auth_client

    response = client.post(
        "/api/auth/me/password",
        json={"current_password": "wrong-pass", "new_password": "new-secure-pass"},
    )
    assert response.status_code == 401
    assert "current password" in response.json()["detail"].lower()
