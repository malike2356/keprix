"""Tests for forgot-password and reset-token flows."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.password_reset_store import password_reset_store
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits

AUDIT_EVENTS: list[tuple[str, dict]] = []


async def _capture_audit(event_type: str, **kwargs):
    AUDIT_EVENTS.append((event_type, kwargs))


@pytest.fixture
def client_bundle(tmp_path, monkeypatch):
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
    monkeypatch.setattr("keprix.auth.password_routes.password_reset_store", password_reset_store)

    async def fake_send(**kwargs):
        fake_send.last_url = kwargs.get("reset_url")
        return False

    fake_send.last_url = None
    monkeypatch.setattr("keprix.auth.password_routes.send_password_reset_email", fake_send)

    client = TestClient(create_app())
    return client, auth, fake_send


def test_forgot_password_sends_for_known_user(client_bundle):
    client, auth, fake_send = client_bundle

    response = client.post("/api/auth/password/forgot", json={"email_or_username": "alice@example.com"})
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    assert fake_send.last_url is not None
    assert any(event[0] == "password_reset_requested" for event in AUDIT_EVENTS)

    user = auth.get_user("alice")
    assert user is not None
    token = fake_send.last_url.split("token=", 1)[1]

    reset = client.post(
        "/api/auth/password/reset",
        json={"token": token, "new_password": "reset-pass-1"},
    )
    assert reset.status_code == 200
    assert any(event[0] == "password_reset_completed" for event in AUDIT_EVENTS)

    login = client.post("/api/auth/login", json={"username": "alice", "password": "reset-pass-1"})
    assert login.status_code == 200


def test_reset_token_single_use(client_bundle):
    client, auth, fake_send = client_bundle
    user = auth.get_user("alice")
    assert user is not None

    client.post("/api/auth/password/forgot", json={"email_or_username": "alice"})
    token = fake_send.last_url.split("token=", 1)[1]

    first = client.post("/api/auth/password/reset", json={"token": token, "new_password": "reset-pass-2"})
    assert first.status_code == 200

    second = client.post("/api/auth/password/reset", json={"token": token, "new_password": "reset-pass-3"})
    assert second.status_code == 400


def test_forgot_password_rate_limited(client_bundle):
    client, _auth, _fake_send = client_bundle

    for _ in range(3):
        response = client.post("/api/auth/password/forgot", json={"email_or_username": "alice@example.com"})
        assert response.status_code == 200

    blocked = client.post("/api/auth/password/forgot", json={"email_or_username": "alice@example.com"})
    assert blocked.status_code == 429


def test_forgot_password_unknown_user_still_generic_success(client_bundle):
    client, _auth, fake_send = client_bundle

    response = client.post("/api/auth/password/forgot", json={"email_or_username": "missing@example.com"})
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]
    assert fake_send.last_url is None
