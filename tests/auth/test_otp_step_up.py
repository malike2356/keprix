"""Tests for email OTP step-up verification."""

from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.otp_store import otp_store
from keprix.auth.session import AuthManager
from keprix.auth.step_up_store import step_up_store
from keprix.security.rate_limiter import reset_rate_limits

SENT_CODES: list[str] = []


async def _capture_otp_email(**kwargs):
    SENT_CODES.append(str(kwargs.get("code")))
    return False


@pytest.fixture
def step_up_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_OTP_STEP_UP", "true")
    reset_rate_limits()
    SENT_CODES.clear()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")
    secret, _uri = auth.totp_setup("alice")
    code = pyotp.TOTP(secret).now()
    assert auth.totp_confirm("alice", code) is True

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.otp_routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.otp_routes.send_otp_email", _capture_otp_email)
    monkeypatch.setattr("keprix.auth.otp_routes.otp_store", otp_store)
    monkeypatch.setattr("keprix.auth.otp_routes.step_up_store", step_up_store)

    client = TestClient(create_app())
    login = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alice-pass", "totp_code": pyotp.TOTP(secret).now()},
    )
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, auth, headers, secret


def test_step_up_allows_totp_disable_without_authenticator_code(step_up_client):
    client, auth, headers, secret = step_up_client

    sent = client.post("/api/auth/otp/send", json={"purpose": "step_up"}, headers=headers)
    assert sent.status_code == 200
    challenge_id = sent.json()["challenge_id"]

    verified = client.post(
        "/api/auth/otp/verify",
        json={"challenge_id": challenge_id, "code": SENT_CODES[-1]},
    )
    assert verified.status_code == 200
    step_up_token = verified.json()["step_up_token"]

    disabled = client.post(
        "/api/auth/totp/disable",
        headers=headers,
        json={"password": "alice-pass", "step_up_token": step_up_token},
    )
    assert disabled.status_code == 200
    assert auth.get_user("alice")["totp_enabled"] is False


def test_step_up_token_single_use(step_up_client):
    client, auth, headers, _secret = step_up_client

    sent = client.post("/api/auth/otp/send", json={"purpose": "step_up"}, headers=headers)
    challenge_id = sent.json()["challenge_id"]
    verified = client.post(
        "/api/auth/otp/verify",
        json={"challenge_id": challenge_id, "code": SENT_CODES[-1]},
    )
    step_up_token = verified.json()["step_up_token"]
    user = auth.get_user("alice")
    assert user is not None

    assert step_up_store.consume(str(user["id"]), step_up_token) is True
    assert step_up_store.consume(str(user["id"]), step_up_token) is False
