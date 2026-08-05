"""Tests for login TOTP and recovery-code flows."""

from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def auth_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    reset_rate_limits()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")
    secret, _uri = auth.totp_setup("alice")
    code = pyotp.TOTP(secret).now()
    assert auth.totp_confirm("alice", code) is True
    auth.generate_recovery_codes("alice")

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)

    client = TestClient(create_app())
    return client, auth, secret


def test_login_requires_totp_when_enabled(auth_bundle):
    client, auth, secret = auth_bundle

    missing = client.post("/api/auth/login", json={"username": "alice", "password": "alice-pass"})
    assert missing.status_code == 403
    assert missing.json()["detail"]["code"] == "totp_required"

    wrong = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass", "totp_code": "000000"},
    )
    assert wrong.status_code == 401

    valid_code = pyotp.TOTP(secret).now()
    ok = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass", "totp_code": valid_code},
    )
    assert ok.status_code == 200
    assert ok.json()["user"]["totp_enabled"] is True


def test_login_accepts_recovery_code_once(auth_bundle):
    client, auth, _secret = auth_bundle
    user = auth.get_user("alice")
    assert user is not None
    codes = auth.generate_recovery_codes("alice")
    recovery = codes[0]

    first = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass", "recovery_code": recovery},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass", "recovery_code": recovery},
    )
    assert second.status_code == 401


def test_disable_totp_requires_password_and_code(auth_bundle):
    client, auth, secret = auth_bundle
    login = client.post(
        "/api/auth/login",
        json={
            "username": "alice",
            "password": "alice-pass",
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    failed = client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={"password": "wrong-pass", "code": pyotp.TOTP(secret).now()},
    )
    assert failed.status_code == 400

    ok = client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={"password": "alice-pass", "code": pyotp.TOTP(secret).now()},
    )
    assert ok.status_code == 200
    assert auth.get_user("alice")["totp_enabled"] is False
