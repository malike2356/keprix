"""Tests for self-service account profile updates."""

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
    auth.create_user("bob", "bob-pass", email="bob@example.com", role="user")

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.routes.audit_log", _capture_audit)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    assert login.status_code == 200
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, auth


def test_patch_me_updates_display_name_and_email(auth_client):
    client, _auth = auth_client

    response = client.patch(
        "/api/auth/me",
        json={
            "display_name": "Alice Example",
            "email": "alice.new@example.com",
            "locale": "fr",
            "timezone": "Europe/Paris",
        },
    )
    assert response.status_code == 200
    body = response.json()["user"]
    assert body["display_name"] == "Alice Example"
    assert body["email"] == "alice.new@example.com"
    assert body["locale"] == "fr"
    assert body["timezone"] == "Europe/Paris"

    me = client.get("/api/auth/me")
    assert me.json()["user"]["display_name"] == "Alice Example"

    assert any(event[0] == "profile_updated" for event in AUDIT_EVENTS)
    profile_event = next(event for event in AUDIT_EVENTS if event[0] == "profile_updated")
    assert "email" in profile_event[1]["event_data"]["fields"]


def test_patch_me_rejects_duplicate_email(auth_client):
    client, _auth = auth_client

    response = client.patch(
        "/api/auth/me",
        json={"email": "bob@example.com"},
    )
    assert response.status_code == 400
    assert "already in use" in response.json()["detail"].lower()


def test_public_user_defaults_display_name_to_username(auth_client):
    _client, auth = auth_client
    user = auth.get_user("alice")
    assert user is not None

    from keprix.auth.routes import _public_user

    public = _public_user(user)
    assert public["display_name"] == "alice"
