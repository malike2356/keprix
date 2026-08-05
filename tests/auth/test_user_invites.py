"""Tests for workspace user invites."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.invite_store import invite_store
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
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
    monkeypatch.setattr("keprix.auth.user_invites.auth_manager", auth)
    monkeypatch.setattr("keprix.api.admin_workspace_routes.auth_manager", auth)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_invite_create_preview_and_accept(admin_client, monkeypatch):
    async def fake_send(**kwargs):
        return False

    monkeypatch.setattr("keprix.auth.user_invites._send_invite_email", fake_send)

    invited = admin_client.post(
        "/api/users/invite",
        json={"email": "teammate@example.com", "role": "user", "message": "Welcome"},
    )
    assert invited.status_code == 200
    body = invited.json()
    assert body["invite"]["email"] == "teammate@example.com"
    assert "invite_url" in body
    assert body["email_sent"] is False

    token = body["invite_url"].split("token=", 1)[1]
    preview = admin_client.get(f"/api/auth/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["invite"]["email"] == "teammate@example.com"

    accepted = admin_client.post(
        "/api/auth/invites/accept",
        json={"token": token, "password": "secure-pass-1", "username": "teammate"},
    )
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["user"]["username"] == "teammate"
    assert payload["token"]

    users = admin_client.get("/api/users")
    assert users.status_code == 200
    emails = [row["email"] for row in users.json()["items"]]
    assert "teammate@example.com" in emails


def test_update_and_delete_user(admin_client, monkeypatch):
    async def fake_send(**kwargs):
        return False

    monkeypatch.setattr("keprix.auth.user_invites._send_invite_email", fake_send)
    invited = admin_client.post(
        "/api/users/invite",
        json={"email": "editor@example.com", "role": "user"},
    )
    token = invited.json()["invite_url"].split("token=", 1)[1]
    accepted = admin_client.post(
        "/api/auth/invites/accept",
        json={"token": token, "password": "secure-pass-2", "username": "editor"},
    )
    user_id = accepted.json()["user"]["id"]

    updated = admin_client.put(
        f"/api/users/{user_id}",
        json={"role": "admin", "status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["role"] == "admin"

    deleted = admin_client.delete(f"/api/users/{user_id}")
    assert deleted.status_code == 200


def test_revoke_pending_invite(admin_client, monkeypatch):
    async def fake_send(**kwargs):
        return False

    monkeypatch.setattr("keprix.auth.user_invites._send_invite_email", fake_send)
    invited = admin_client.post(
        "/api/users/invite",
        json={"email": "pending@example.com", "role": "user"},
    )
    invite_id = invited.json()["invite"]["id"]
    revoked = admin_client.delete(f"/api/users/invites/{invite_id}")
    assert revoked.status_code == 200
    assert invite_store.get(invite_id)["status"] == "revoked"
