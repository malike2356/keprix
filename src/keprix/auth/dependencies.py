"""FastAPI auth dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.auth.config import auth_enabled
from keprix.auth.session import auth_manager
from keprix.keys.local_access import effective_access_level

_bearer = HTTPBearer(auto_error=False)


def _extract_bearer(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")


def _extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    bearer = _extract_bearer(request, credentials)
    if bearer:
        return bearer
    return request.cookies.get("keprix_session")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Resolve the caller.

    Order:
    1. ``kp_`` API keys (strict path scopes for /api/*)
    2. Guest when auth disabled
    3. Loopback developer identity
    4. Session Bearer / cookie
    """
    bearer = _extract_bearer(request, credentials)
    if bearer and bearer.startswith("kp_"):
        from keprix.public_api.auth import (
            api_key_as_user,
            check_api_path_allowed,
            require_api_key,
        )

        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=bearer)
        ctx = await require_api_key(request, creds)
        check_api_path_allowed(ctx, path=request.url.path, method=request.method)
        user = api_key_as_user(ctx)
        request.state.auth_via = "api_key"
        request.state.api_key = ctx
        request.state.user = user
        return user

    if not auth_enabled():
        user = auth_manager.guest_user()
        request.state.user = user
        return user

    token = _extract_token(request, credentials)
    if not token:
        client_host = (request.client.host if request.client else "") or ""
        if client_host in ("127.0.0.1", "::1", "localhost") and effective_access_level() == "developer":
            user = auth_manager.guest_user()
            request.state.user = user
            return user
        raise HTTPException(status_code=401, detail="Authentication required")

    # Opaque session tokens only; kp_ keys handled above.
    if token.startswith("kp_"):
        raise HTTPException(status_code=401, detail="Invalid or unauthorized API key")

    user = auth_manager.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    auth_manager.touch_session(token)
    request.state.auth_token = token
    request.state.user = user
    return user


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    if not auth_enabled():
        return auth_manager.guest_user()
    bearer = _extract_bearer(request, credentials)
    if bearer and bearer.startswith("kp_"):
        try:
            return await get_current_user(request, credentials)
        except HTTPException:
            return None
    token = _extract_token(request, credentials)
    if not token:
        return None
    user = auth_manager.validate_token(token)
    if not user:
        return None
    request.state.auth_token = token
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
