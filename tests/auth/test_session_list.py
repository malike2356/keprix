"""Tests for active session list and revoke APIs."""

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
def session_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()
    AUDIT_EVENTS.clear()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.session_routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.session_routes.audit_log", _capture_audit)

    client = TestClient(create_app())
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass"},
        headers={"X-Client-Label": "Test Browser"},
    )
    token = login.json()["token"]
    other_token = auth.create_session("alice", device_label="Other device", ip_address="10.0.0.9")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, auth, token, other_token


def test_list_sessions_marks_current(session_client):
    client, _auth, _token, _other = session_client
    response = client.get("/api/auth/sessions")
    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert len(sessions) == 2
    current = [row for row in sessions if row["is_current"]]
    assert len(current) == 1
    assert current[0]["device_label"] == "Test Browser"


def test_revoke_other_session_invalidates_token(session_client):
    client, auth, token, other_token = session_client
    listed = client.get("/api/auth/sessions").json()["sessions"]
    target = next(row for row in listed if not row["is_current"])

    revoked = client.delete(f"/api/auth/sessions/{target['session_id']}")
    assert revoked.status_code == 200

    other_client = TestClient(create_app())
    check = other_client.get("/api/auth/me", headers={"Authorization": f"Bearer {other_token}"})
    assert check.status_code == 401
    assert auth.validate_token(token) is not None


def test_revoke_current_session_rejected(session_client):
    client, _auth, _token, _other = session_client
    listed = client.get("/api/auth/sessions").json()["sessions"]
    current = next(row for row in listed if row["is_current"])
    response = client.delete(f"/api/auth/sessions/{current['session_id']}")
    assert response.status_code == 404


def test_revoke_others_keeps_current(session_client):
    client, auth, token, other_token = session_client
    response = client.post("/api/auth/sessions/revoke-others")
    assert response.status_code == 200
    assert response.json()["removed"] == 1
    assert auth.validate_token(token) is not None
    assert auth.validate_token(other_token) is None
    assert any(event[0] == "sessions_revoked_all" for event in AUDIT_EVENTS)


def test_registry_loads_only_user_sessions(session_client):
    client, auth, _token, _other = session_client
    auth.create_user("bob", "bob-pass", email="bob@example.com", role="user")
    auth.create_session("bob", device_label="Bob laptop")
    response = client.get("/api/auth/sessions")
    usernames = {row["device_label"] for row in response.json()["sessions"]}
    assert "Bob laptop" not in usernames
