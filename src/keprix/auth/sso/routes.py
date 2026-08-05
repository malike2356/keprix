"""Workspace SSO HTTP routes."""

from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from keprix.auth.config import auth_enabled
from keprix.auth.dependencies import get_current_user, get_optional_current_user
from keprix.auth.request_context import client_ip as resolve_client_ip, client_label
from keprix.auth.session import auth_manager
from keprix.auth.sso.models import InvalidSsoStateError, SsoProviderError
from keprix.auth.sso.registry import get_provider, list_providers, reload_registry
from keprix.auth.sso.service import resolve_sso_user
from keprix.auth.sso.store import sso_store
from keprix.security.audit import audit_log

router = APIRouter(prefix="/api/auth/sso", tags=["auth-sso"])

STATE_COOKIE = "keprix_sso_oauth"
STATE_TTL_SECONDS = 600


class SsoLinkStartRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    return_to: str | None = Field(None, max_length=512)


class SsoUnlinkRequest(BaseModel):
    password: str | None = None
    step_up_token: str | None = None


def _frontend_url() -> str:
    return os.getenv("KEPRIX_FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")


def _sso_redirect_uri(request: Request) -> str:
    explicit = os.getenv("KEPRIX_SSO_REDIRECT_URI", "").strip()
    if explicit:
        return explicit.rstrip("/")
    return str(request.url_for("sso_callback"))


def _cookie_secure(request: Request) -> bool:
    forwarded = request.headers.get("x-forwarded-proto", "")
    if forwarded:
        return forwarded.split(",")[0].strip().lower() == "https"
    return request.url.scheme == "https"


def _validate_return_to(raw: str | None) -> str:
    if not raw:
        return "/launcher"
    value = raw.strip()
    if not value.startswith("/") or value.startswith("//"):
        return "/launcher"
    return value


def _encode_state_cookie(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_state_cookie(raw: str) -> dict[str, Any] | None:
    value = urllib.parse.unquote(raw)
    try:
        decoded = base64.urlsafe_b64decode(value.encode("ascii"))
        data = json.loads(decoded.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        try:
            data = json.loads(value)
            if isinstance(data, str):
                data = json.loads(data)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _set_state_cookie(response: RedirectResponse, request: Request, payload: dict[str, Any]) -> None:
    response.set_cookie(
        STATE_COOKIE,
        _encode_state_cookie(payload),
        httponly=True,
        samesite="lax",
        max_age=STATE_TTL_SECONDS,
        secure=_cookie_secure(request),
        path="/",
    )


def _read_state_cookie(request: Request) -> dict[str, Any] | None:
    raw = request.cookies.get(STATE_COOKIE)
    if not raw:
        return None
    return _decode_state_cookie(raw)


def _clear_state_cookie(response: RedirectResponse, request: Request) -> None:
    response.delete_cookie(STATE_COOKIE, path="/", secure=_cookie_secure(request))


def _error_redirect(message: str, *, return_to: str = "/auth/login") -> RedirectResponse:
    params = urllib.parse.urlencode({"error": message, "return_to": return_to})
    return RedirectResponse(f"{_frontend_url()}/auth/sso/callback?{params}")


@router.get("/providers")
async def sso_providers() -> dict[str, Any]:
    reload_registry()
    return {"providers": list_providers()}


@router.get("/links")
async def sso_links(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"links": sso_store.list_for_user(str(user["id"]))}


@router.get("/{provider}/start", name="sso_start")
async def sso_start(
    provider: str,
    request: Request,
    return_to: str | None = None,
    mode: str = "login",
    user: dict | None = Depends(get_optional_current_user),
) -> RedirectResponse:
    reload_registry()
    config = get_provider(provider)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown or disabled SSO provider")

    if mode == "link":
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required to link provider")
    elif not auth_enabled():
        raise HTTPException(status_code=503, detail="Authentication is disabled")

    state = secrets.token_urlsafe(24)
    redirect_uri = _sso_redirect_uri(request)
    try:
        auth_url = await config.authorization_url(state=state, redirect_uri=redirect_uri)
    except SsoProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payload = {
        "state": state,
        "provider": config.name,
        "return_to": _validate_return_to(return_to),
        "mode": "link" if mode == "link" else "login",
        "link_user_id": str(user["id"]) if mode == "link" and user else None,
    }
    response = RedirectResponse(auth_url, status_code=302)
    _set_state_cookie(response, request, payload)
    return response


@router.get("/callback", name="sso_callback")
async def sso_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    return_to = "/launcher"
    stored = _read_state_cookie(request)
    if stored:
        return_to = _validate_return_to(str(stored.get("return_to") or return_to))

    if error:
        response = _error_redirect(error, return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    if not code or not state or not stored:
        response = _error_redirect("Missing OAuth callback parameters", return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    if state != stored.get("state"):
        response = _error_redirect("Invalid OAuth state", return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    provider_name = str(stored.get("provider") or "")
    reload_registry()
    config = get_provider(provider_name)
    if config is None:
        response = _error_redirect("SSO provider is not configured", return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    redirect_uri = _sso_redirect_uri(request)
    try:
        profile = await config.exchange_code(code=code, redirect_uri=redirect_uri)
    except (SsoProviderError, InvalidSsoStateError) as exc:
        response = _error_redirect(str(exc), return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    link_user_id = stored.get("link_user_id")
    mode = str(stored.get("mode") or "login")
    client_ip = request.client.host if request.client else "unknown"

    try:
        user = resolve_sso_user(
            auth_manager,
            sso_store,
            profile,
            link_user_id=str(link_user_id) if mode == "link" and link_user_id else None,
        )
    except ValueError as exc:
        response = _error_redirect(str(exc), return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    if not user.get("is_active", True):
        response = _error_redirect("Account is disabled", return_to=return_to)
        _clear_state_cookie(response, request)
        return response

    if mode == "link":
        await audit_log(
            "sso_link",
            user_id=user.get("id"),
            ip_address=client_ip,
            event_data={"provider": profile.provider},
        )
        params = urllib.parse.urlencode({"linked": profile.provider, "return_to": return_to})
        response = RedirectResponse(f"{_frontend_url()}/auth/sso/callback?{params}")
        _clear_state_cookie(response, request)
        return response

    token = auth_manager.create_session(
        user["username"],
        device_label=client_label(request),
        ip_address=resolve_client_ip(request),
    )
    await audit_log(
        "sso_login",
        user_id=user.get("id"),
        ip_address=client_ip,
        event_data={"provider": profile.provider},
    )
    params = urllib.parse.urlencode({"token": token, "return_to": return_to})
    response = RedirectResponse(f"{_frontend_url()}/auth/sso/callback?{params}")
    _clear_state_cookie(response, request)
    return response


@router.post("/link")
async def sso_link_start(
    body: SsoLinkStartRequest,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    reload_registry()
    config = get_provider(body.provider)
    if config is None:
        raise HTTPException(status_code=404, detail="Unknown or disabled SSO provider")
    return_to = _validate_return_to(body.return_to or "/settings/account/connected-accounts")
    start_url = f"/api/auth/sso/{config.name}/start?mode=link&return_to={urllib.parse.quote(return_to)}"
    return {"start_url": start_url}


@router.delete("/link/{provider}")
async def sso_unlink(
    provider: str,
    body: SsoUnlinkRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, bool]:
    provider_name = provider.strip().lower()
    links = sso_store.list_for_user(str(user["id"]))
    if not any(str(row.get("provider") or "").lower() == provider_name for row in links):
        raise HTTPException(status_code=404, detail="Provider is not linked")

    verified = False
    if body.step_up_token:
        from keprix.auth.step_up_store import step_up_store

        verified = step_up_store.consume(str(user["id"]), body.step_up_token)
    elif body.password:
        verified = auth_manager.verify_user_password(str(user["id"]), body.password)

    if not verified:
        raise HTTPException(status_code=401, detail="Password or email step-up verification required")

    if sso_store.count_for_user(str(user["id"])) <= 1 and not body.password:
        raise HTTPException(
            status_code=400,
            detail="Set a password before unlinking your only sign-in method",
        )

    if not sso_store.unlink(str(user["id"]), provider_name):
        raise HTTPException(status_code=404, detail="Provider is not linked")

    await audit_log(
        "sso_unlink",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
        event_data={"provider": provider_name},
    )
    return {"ok": True}
