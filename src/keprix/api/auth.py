"""API authentication dependencies."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.auth.config import auth_enabled
from keprix.keys.local_access import effective_access_level

_bearer = HTTPBearer(auto_error=False)

PUBLIC_PATHS = frozenset(
    {
        "/api/health",
        "/api/v1/health",
        "/api/health/scout",
        "/api/health/security",
        "/api/health/products",
        "/api/auth/login",
        "/api/auth/config",
        "/api/v1/auth/login",
        "/openapi.json",
        "/docs",
        "/redoc",
    }
)


def _token_from_request(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip() or None
    api_key = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if api_key:
        return api_key
    cookie = request.cookies.get("keprix_session")
    return cookie or None


def _session_principal(token: str) -> str | None:
    """Map a UI login session token to an API auth principal."""
    if not token or token.startswith("kp_"):
        return None
    try:
        from keprix.auth.session import auth_manager

        user = auth_manager.validate_token(token)
    except Exception:
        return None
    if not user:
        return None
    role = str(user.get("role") or "user").strip().lower()
    if role == "developer":
        return "developer"
    if role in {"admin", "owner"}:
        return "admin"
    return str(user.get("id") or user.get("username") or "user")


async def optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str | None:
    token = _token_from_request(request, credentials)
    if not token:
        client_host = (request.client.host if request.client else "") or ""
        if client_host in ("127.0.0.1", "::1", "localhost") and effective_access_level() == "developer":
            return "developer"
        return None
    api_token = os.environ.get("KEPRIX_API_TOKEN", "")
    if api_token and token == api_token:
        return "api-user"
    admin_token = os.environ.get("KEPRIX_API_ADMIN_TOKEN", "")
    if admin_token and token == admin_token:
        return "admin"
    session_user = _session_principal(token)
    if session_user:
        return session_user
    if effective_access_level() == "developer":
        return "developer"
    return None


async def require_api_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if request.url.path in PUBLIC_PATHS:
        return "public"
    if not auth_enabled():
        return "local"
    user = await optional_user(request, credentials)
    if user:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
    )


async def require_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    user = await optional_user(request, credentials)
    if user in {"admin", "developer"}:
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )
