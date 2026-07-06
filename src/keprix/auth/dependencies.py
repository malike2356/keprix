"""FastAPI auth dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.auth.config import auth_enabled
from keprix.auth.session import auth_manager
from keprix.keys.local_access import effective_access_level

_bearer = HTTPBearer(auto_error=False)


def _extract_token(request: Request, credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get("keprix_session")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if not auth_enabled():
        return auth_manager.guest_user()
    token = _extract_token(request, credentials)
    if not token:
        client_host = (request.client.host if request.client else "") or ""
        if client_host in ("127.0.0.1", "::1", "localhost") and effective_access_level() == "developer":
            return auth_manager.guest_user()
        raise HTTPException(status_code=401, detail="Authentication required")
    user = auth_manager.validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    request.state.auth_token = token
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
