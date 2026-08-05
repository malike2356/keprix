from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest

from keprix.auth.studio_handoff import (
    STUDIO_HANDOFF_AUDIENCE,
    StudioHandoffError,
    handoff_username,
    verify_studio_handoff_token,
)


def _sign_token(claims: dict, secret: str) -> str:
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signature = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{body}.{sig}"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_HANDOFF_SECRET", "test-handoff-secret-1234")


def test_verify_studio_handoff_token_accepts_valid_claims() -> None:
    now = int(time.time())
    token = _sign_token(
        {
            "sub": "operator@example.com",
            "tenant_id": "tenant-1",
            "carina_user_id": "user-9",
            "aud": STUDIO_HANDOFF_AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        "test-handoff-secret-1234",
    )
    claims = verify_studio_handoff_token(token, now=now)
    assert claims.tenant_id == "tenant-1"
    assert claims.carina_user_id == "user-9"
    assert handoff_username(claims).startswith("carina-tenant-1-user-9")


def test_verify_studio_handoff_token_rejects_expired_token() -> None:
    now = int(time.time())
    token = _sign_token(
        {
            "sub": "operator@example.com",
            "tenant_id": "tenant-1",
            "carina_user_id": "user-9",
            "aud": STUDIO_HANDOFF_AUDIENCE,
            "iat": now - 400,
            "exp": now - 60,
        },
        "test-handoff-secret-1234",
    )
    with pytest.raises(StudioHandoffError):
        verify_studio_handoff_token(token, now=now)


def test_consume_handoff_route_mints_session() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from keprix.api.handoff_routes import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    now = int(time.time())
    token = _sign_token(
        {
            "sub": "carina.user@example.com",
            "tenant_id": "tenant-abc",
            "carina_user_id": "carina-42",
            "aud": STUDIO_HANDOFF_AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        "test-handoff-secret-1234",
    )
    response = client.post("/api/auth/handoff/consume", json={"token": token})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token"]
    assert payload["user"]["workspace_id"] == "tenant-abc"
    assert payload["user"]["auth_source"] == "carina_handoff"

    replay = client.post("/api/auth/handoff/consume", json={"token": token})
    assert replay.status_code == 401
