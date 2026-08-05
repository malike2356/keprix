"""Auth and security tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def auth_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "correct-horse-battery")
    monkeypatch.setenv("KEPRIX_ADMIN_EMAIL", "")
    monkeypatch.setenv("ADMIN_EMAIL", "")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "false")
    reset_rate_limits()
    auth = AuthManager(str(tmp_path / "auth.json"))
    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.admin_routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    return auth


@pytest.fixture
def client(auth_env):
    return TestClient(create_app())


def test_auth_config_endpoint(client):
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    body = response.json()
    assert body["auth_enabled"] is True
    assert body["multi_user"] is False


def test_login_returns_bearer_token(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "correct-horse-battery"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user"]["username"] == "admin"


def test_login_wrong_password_six_times_returns_429(client):
    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert response.status_code == 401
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "600"


def test_security_headers_present(client):
    response = client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


def test_redact_replaces_anthropic_key():
    from keprix.security.redact import redact_text

    secret = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz1234567890"
    redacted = redact_text(f"token={secret}")
    assert secret not in redacted
    assert "REDACTED" in redacted
