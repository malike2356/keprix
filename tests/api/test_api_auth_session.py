"""Tests for API auth accepting UI session tokens."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from keprix.api import auth as api_auth


def _request(headers: dict[str, str] | None = None, cookies: dict[str, str] | None = None) -> Request:
    header_list = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/browser/sessions",
        "raw_path": b"/api/browser/sessions",
        "query_string": b"",
        "headers": header_list,
        "client": ("172.26.0.5", 12345),
        "server": ("keprix-backend", 3333),
    }
    req = Request(scope)
    if cookies:
        # Starlette reads cookies from header
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        scope["headers"] = list(scope["headers"]) + [(b"cookie", cookie_header.encode())]
        req = Request(scope)
    return req


@pytest.mark.asyncio
async def test_require_api_auth_accepts_session_token(monkeypatch):
    monkeypatch.setattr(api_auth, "auth_enabled", lambda: True)
    monkeypatch.setattr(api_auth, "effective_access_level", lambda: "standard")
    monkeypatch.setattr(
        api_auth,
        "_session_principal",
        lambda token: "user-1" if token == "sess_ok" else None,
    )
    req = _request({"Authorization": "Bearer sess_ok"})
    principal = await api_auth.require_api_auth(req, credentials=None)
    assert principal == "user-1"


@pytest.mark.asyncio
async def test_require_api_auth_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(api_auth, "auth_enabled", lambda: True)
    monkeypatch.setattr(api_auth, "effective_access_level", lambda: "standard")
    monkeypatch.setattr(api_auth, "_session_principal", lambda token: None)
    req = _request()
    with pytest.raises(HTTPException) as exc:
        await api_auth.require_api_auth(req, credentials=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_optional_user_accepts_session_cookie(monkeypatch):
    monkeypatch.setattr(api_auth, "effective_access_level", lambda: "standard")
    monkeypatch.setattr(
        api_auth,
        "_session_principal",
        lambda token: "admin" if token == "cookie-token" else None,
    )
    req = _request(cookies={"keprix_session": "cookie-token"})
    principal = await api_auth.optional_user(req, credentials=None)
    assert principal == "admin"
