"""Tests for Prompt 137: admin workspace pages API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.public_api.keys import ApiKeyStore
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def admin_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.api.admin_workspace_routes.auth_manager", auth)

    key_store = ApiKeyStore(path=tmp_path / "api_keys.json")
    monkeypatch.setattr("keprix.api.admin_workspace_routes.get_api_key_store", lambda: key_store)

    client = TestClient(create_app())
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin-pass"})
    token = login.json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_list_tools_returns_builtin_and_counts(admin_client):
    response = admin_client.get("/api/tools")
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["builtin"] >= 1
    assert len(payload["items"]) >= 1
    assert {"id", "name", "description", "source", "status"}.issubset(payload["items"][0].keys())


def test_get_tool_includes_usage_series(admin_client):
    listing = admin_client.get("/api/tools").json()
    tool_id = listing["items"][0]["id"]
    detail = admin_client.get(f"/api/tools/{tool_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert "usage" in body
    assert "labels" in body["usage"]
    assert "values" in body["usage"]


def test_memory_documents_list_and_upload(admin_client):
    listed = admin_client.get("/api/memory/documents")
    assert listed.status_code == 200
    assert "items" in listed.json()
    assert "stats" in listed.json()

    uploaded = admin_client.post(
        "/api/memory/documents",
        files={"file": ("notes.md", b"# Notes\n\nHello memory.", "text/markdown")},
    )
    assert uploaded.status_code == 200
    doc = uploaded.json()
    assert doc["id"]
    assert doc["status"] == "indexed"

    fetched = admin_client.get(f"/api/memory/documents/{doc['id']}")
    assert fetched.status_code == 200
    assert "Hello memory" in fetched.json().get("preview", "")


def test_memory_url_index_fetches_content(admin_client, monkeypatch):
    async def fake_fetch(url: str):
        return "Example Page", f"Fetched body for {url}"

    monkeypatch.setattr("keprix.api.admin_workspace_routes.fetch_page_text", fake_fetch)
    indexed = admin_client.post("/api/memory/documents/url", json={"url": "https://example.com/docs"})
    assert indexed.status_code == 200
    body = indexed.json()
    assert body["name"] == "Example Page"
    assert "Fetched body" in body["preview"]
    assert "Indexed URL placeholder" not in body["preview"]


def test_channels_overview_and_telegram_config(admin_client):
    overview = admin_client.get("/api/channels/overview")
    assert overview.status_code == 200
    channels = {item["id"]: item for item in overview.json()["channels"]}
    assert {"telegram", "discord", "rest"}.issubset(channels.keys())

    config = admin_client.get("/api/channels/telegram")
    assert config.status_code == 200
    assert "webhook_url" in config.json()

    saved = admin_client.post("/api/channels/telegram", json={"bot_token": "test-token"})
    assert saved.status_code == 200
    tested = admin_client.post("/api/channels/telegram/test")
    assert tested.status_code == 200
    assert tested.json()["ok"] is True


def test_api_keys_create_and_revoke(admin_client):
    created = admin_client.post(
        "/api/api-keys",
        json={"name": "ci-key", "expiry": "none", "scopes": ["read", "write"]},
    )
    assert created.status_code == 200
    body = created.json()
    assert body.get("secret")
    key_id = body["id"]

    listed = admin_client.get("/api/api-keys")
    assert any(item["id"] == key_id for item in listed.json()["keys"])

    revoked = admin_client.delete(f"/api/api-keys/{key_id}")
    assert revoked.status_code == 200


def test_settings_get_and_update(admin_client):
    current = admin_client.get("/api/settings")
    assert current.status_code == 200
    assert "settings" in current.json()
    assert "providers" in current.json()

    updated = admin_client.put("/api/settings", json={"instance_name": "Keprix Test"})
    assert updated.status_code == 200
    assert updated.json()["settings"]["instance_name"] == "Keprix Test"


def test_users_list_and_invite(admin_client, monkeypatch):
    async def fake_send(**kwargs):
        return False

    monkeypatch.setattr("keprix.auth.user_invites._send_invite_email", fake_send)

    users = admin_client.get("/api/users")
    assert users.status_code == 200
    assert users.json()["stats"]["total"] >= 1

    invited = admin_client.post(
        "/api/users/invite",
        json={"email": "teammate@example.com", "role": "user", "message": "Join us"},
    )
    assert invited.status_code == 200
    assert invited.json()["invite"]["email"] == "teammate@example.com"
