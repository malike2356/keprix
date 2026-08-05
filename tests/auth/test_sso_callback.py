"""Tests for SSO OAuth callback and user provisioning."""

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
def sso_env(tmp_path, monkeypatch):
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
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")
    identities = SsoIdentityStore(str(tmp_path / "oauth_identities.json"))

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.sso.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.sso.routes.sso_store", identities)

    async def _mock_google_exchange(*, client_id, client_secret, code, redirect_uri):
        del client_id, client_secret, redirect_uri
        return SsoProfile(
            provider="google",
            subject="google-sub-new",
            email="newuser@example.com",
            name="New User",
            avatar_url="https://example.com/a.png",
        )

    monkeypatch.setattr("keprix.auth.sso.providers.google.exchange_code", _mock_google_exchange)

    client = TestClient(create_app())
    return client, auth, identities


def test_providers_lists_enabled(sso_env):
    client, _auth, _store = sso_env
    response = client.get("/api/auth/sso/providers")
    assert response.status_code == 200
    names = [row["name"] for row in response.json()["providers"]]
    assert "google" in names


def _parse_state_cookie(raw: str | None) -> dict:
    if not raw:
        raise ValueError("missing cookie")
    value = urllib.parse.unquote(raw)
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        data = json.loads(value)
        if isinstance(data, str):
            data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError("invalid cookie payload")
    return data


REDIRECT_CODES = {302, 307}


def test_callback_creates_session_for_new_user(sso_env):
    client, auth, store = sso_env
    start = client.get("/api/auth/sso/google/start?return_to=/launcher", follow_redirects=False)
    assert start.status_code == 302
    assert "accounts.google.com" in start.headers["location"]
    cookie = start.cookies.get("keprix_sso_oauth")
    assert cookie
    payload = _parse_state_cookie(cookie)
    state = payload["state"]

    callback = client.get(
        f"/api/auth/sso/callback?code=new-user-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code in REDIRECT_CODES
    assert callback.headers["location"].startswith("http://frontend.test/auth/sso/callback?")
    assert "token=" in callback.headers["location"]

    user_id = store.get_user_id("google", "google-sub-new")
    assert user_id
    assert auth.get_user_by_id(user_id) is not None


def test_callback_links_existing_email(sso_env, monkeypatch):
    client, auth, store = sso_env

    async def _link_exchange(*, client_id, client_secret, code, redirect_uri):
        del client_id, client_secret, code, redirect_uri
        return SsoProfile(
            provider="google",
            subject="google-sub-alice",
            email="alice@example.com",
            name="Alice Example",
            avatar_url=None,
        )

    monkeypatch.setattr("keprix.auth.sso.providers.google.exchange_code", _link_exchange)

    start = client.get("/api/auth/sso/google/start?return_to=/projects", follow_redirects=False)
    cookie = start.cookies.get("keprix_sso_oauth")
    payload = _parse_state_cookie(cookie)
    state = payload["state"]

    callback = client.get(
        f"/api/auth/sso/callback?code=link-code&state={state}",
        follow_redirects=False,
    )
    assert callback.status_code in REDIRECT_CODES
    alice = auth.get_user("alice")
    assert alice is not None
    assert store.get_user_id("google", "google-sub-alice") == alice["id"]


def test_registry_ignores_unconfigured_providers(sso_env, monkeypatch):
    monkeypatch.delenv("KEPRIX_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("KEPRIX_GITHUB_CLIENT_SECRET", raising=False)
    reload_registry()
    client, _auth, _store = sso_env
    response = client.get("/api/auth/sso/providers")
    names = [row["name"] for row in response.json()["providers"]]
    assert "github" not in names
