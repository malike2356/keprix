"""Tests for SSO link and unlink rules."""

from __future__ import annotations

import base64
import json
import urllib.parse

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.auth.sso.models import SsoProfile
from keprix.auth.sso.registry import reload_registry
from keprix.auth.sso.store import SsoIdentityStore
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def sso_link_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_FRONTEND_URL", "http://frontend.test")
    monkeypatch.setenv("KEPRIX_GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("KEPRIX_GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("KEPRIX_SSO_REDIRECT_URI", "http://testserver/api/auth/sso/callback")
    reset_rate_limits()
    reload_registry()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("bob", "bob-pass", email="bob@example.com", role="user")
    identities = SsoIdentityStore(str(tmp_path / "oauth_identities.json"))
    identities.link(
        str(auth.get_user("bob")["id"]),
        SsoProfile(provider="google", subject="sub-bob", email="bob@example.com", name="Bob", avatar_url=None),
    )

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.sso.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.sso.routes.sso_store", identities)

    client = TestClient(create_app())
    token = auth.create_session("bob")
    return client, auth, identities, token


def test_link_start_requires_auth(sso_link_client):
    client, _auth, _store, _token = sso_link_client
    response = client.post("/api/auth/sso/link", json={"provider": "google"})
    assert response.status_code == 401


def test_link_start_returns_url(sso_link_client):
    client, _auth, _store, token = sso_link_client
    response = client.post(
        "/api/auth/sso/link",
        json={"provider": "google", "return_to": "/settings/account/connected-accounts"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert "/api/auth/sso/google/start" in response.json()["start_url"]


def test_list_links_for_user(sso_link_client):
    client, _auth, _store, token = sso_link_client
    response = client.get("/api/auth/sso/links", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    links = response.json()["links"]
    assert len(links) == 1
    assert links[0]["provider"] == "google"


def test_unlink_requires_verification(sso_link_client):
    client, _auth, _store, token = sso_link_client
    response = client.request(
        "DELETE",
        "/api/auth/sso/link/google",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_unlink_with_password(sso_link_client):
    client, auth, store, token = sso_link_client
    response = client.request(
        "DELETE",
        "/api/auth/sso/link/google",
        json={"password": "bob-pass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    bob = auth.get_user("bob")
    assert store.count_for_user(str(bob["id"])) == 0


def test_link_mode_redirect(sso_link_client, monkeypatch):
    client, auth, store, token = sso_link_client

    async def _mock_exchange(*, client_id, client_secret, code, redirect_uri):
        del client_id, client_secret, code, redirect_uri
        return SsoProfile(
            provider="github",
            subject="gh-99",
            email="bob@example.com",
            name="Bob",
            avatar_url=None,
        )

    monkeypatch.setenv("KEPRIX_GITHUB_CLIENT_ID", "gh-client")
    monkeypatch.setenv("KEPRIX_GITHUB_CLIENT_SECRET", "gh-secret")
    reload_registry()
    monkeypatch.setattr("keprix.auth.sso.providers.github.exchange_code", _mock_exchange)

    start = client.get(
        "/api/auth/sso/github/start?mode=link&return_to=/settings/account/connected-accounts",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=False,
    )
    assert start.status_code == 302
    cookie = start.cookies.get("keprix_sso_oauth")
    raw = urllib.parse.unquote(cookie or "")
    try:
        payload = json.loads(base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        payload = json.loads(raw)
        if isinstance(payload, str):
            payload = json.loads(payload)
    state = payload["state"]
    callback = client.get(
        f"/api/auth/sso/callback?code=abc&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code in {302, 307}
    assert "linked=github" in callback.headers["location"]
    bob = auth.get_user("bob")
    assert store.get_user_id("github", "gh-99") == bob["id"]
