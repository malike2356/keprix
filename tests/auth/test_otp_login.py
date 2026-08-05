"""Tests for email OTP login."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.otp_store import otp_store
from keprix.auth.session import AuthManager
from keprix.security.rate_limiter import reset_rate_limits

SENT_CODES: list[str] = []


async def _capture_otp_email(**kwargs):
    SENT_CODES.append(str(kwargs.get("code")))
    return False


@pytest.fixture
def otp_client(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_ADMIN_PASSWORD", "admin-pass")
    monkeypatch.setenv("KEPRIX_MULTI_USER", "true")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("KEPRIX_OTP_LOGIN", "true")
    reset_rate_limits()
    SENT_CODES.clear()

    auth = AuthManager(str(tmp_path / "auth.json"))
    auth.create_user("alice", "alice-pass", email="alice@example.com", role="user")

    monkeypatch.setattr("keprix.auth.routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.otp_routes.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.dependencies.auth_manager", auth)
    monkeypatch.setattr("keprix.auth.otp_routes.send_otp_email", _capture_otp_email)
    monkeypatch.setattr("keprix.auth.otp_routes.otp_store", otp_store)

    client = TestClient(create_app())
    return client, auth


def test_otp_send_and_login(otp_client):
    client, _auth = otp_client

    sent = client.post("/api/auth/otp/send", json={"email_or_username": "alice@example.com", "purpose": "login"})
    assert sent.status_code == 200
    body = sent.json()
    assert body["challenge_id"]
    assert len(SENT_CODES) == 1

    bad = client.post(
        "/api/auth/otp/verify",
        json={"challenge_id": body["challenge_id"], "code": "000000"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/auth/otp/verify",
        json={"challenge_id": body["challenge_id"], "code": SENT_CODES[0]},
    )
    assert ok.status_code == 200
    payload = ok.json()
    assert payload["token"]
    assert payload["user"]["username"] == "alice"


def test_otp_send_unknown_user_generic_success(otp_client):
    client, _auth = otp_client
    response = client.post("/api/auth/otp/send", json={"email_or_username": "missing@example.com", "purpose": "login"})
    assert response.status_code == 200
    assert "challenge_id" not in response.json()


def test_otp_send_rate_limited(otp_client):
    client, _auth = otp_client
    for _ in range(5):
        response = client.post("/api/auth/otp/send", json={"email_or_username": "alice", "purpose": "login"})
        assert response.status_code == 200
    blocked = client.post("/api/auth/otp/send", json={"email_or_username": "alice", "purpose": "login"})
    assert blocked.status_code == 429


def test_otp_expired_rejected(otp_client, monkeypatch):
    client, auth = otp_client
    sent = client.post("/api/auth/otp/send", json={"email_or_username": "alice", "purpose": "login"})
    challenge_id = sent.json()["challenge_id"]
    code = SENT_CODES[-1]

    user = auth.get_user("alice")
    assert user is not None

    path = otp_store._read()
    record = path.get(challenge_id)
    assert record is not None
    record["expires_at"] = time.time() - 1
    otp_store._write({**path, challenge_id: record})

    expired = client.post("/api/auth/otp/verify", json={"challenge_id": challenge_id, "code": code})
    assert expired.status_code == 400


def test_otp_max_attempts(otp_client):
    client, _auth = otp_client
    sent = client.post("/api/auth/otp/send", json={"email_or_username": "alice", "purpose": "login"})
    challenge_id = sent.json()["challenge_id"]

    for _ in range(5):
        response = client.post("/api/auth/otp/verify", json={"challenge_id": challenge_id, "code": "000000"})
        assert response.status_code == 400

    locked = client.post("/api/auth/otp/verify", json={"challenge_id": challenge_id, "code": "000000"})
    assert locked.status_code == 400
