"""Authentication for the public developer API."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.auth.config import auth_enabled
from keprix.auth.session import auth_manager
from keprix.keys.local_access import effective_access_level
from keprix.public_api.keys import ApiKeyContext, get_api_key_store

_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ApiKeyContext:
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Missing API key", "code": "invalid_api_key"},
        )

    env_token = os.environ.get("KEPRIX_API_TOKEN", "")
    if env_token and token == env_token:
        return ApiKeyContext(
            key_id="env-token",
            workspace_id="default",
            role="developer",
            allowed_models=[],
            allowed_endpoints=[],
            monthly_limit=None,
            usage_this_month=0,
            scopes={"tools:execute": True},
        )

    ctx = get_api_key_store().authenticate(token)
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid API key", "code": "invalid_api_key"},
        )

    if ctx.monthly_limit is not None and ctx.usage_this_month >= ctx.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Monthly usage limit exceeded", "code": "usage_limit_exceeded"},
        )

    request.state.api_key = ctx
    return ctx


async def require_developer_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    admin_token = os.environ.get("KEPRIX_API_ADMIN_TOKEN", "")
    token = _extract_token(request, credentials)
    if admin_token and token == admin_token:
        return "admin"
    if effective_access_level() == "developer":
        return "developer"
    if not auth_enabled():
        return "local"
    if token and auth_manager.validate_token(token):
        return "session"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Developer access required", "code": "forbidden"},
    )


def check_endpoint_allowed(ctx: ApiKeyContext, endpoint: str) -> None:
    if not ctx.allowed_endpoints:
        return
    if endpoint not in ctx.allowed_endpoints:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Endpoint not allowed: {endpoint}", "code": "endpoint_forbidden"},
        )


def check_model_allowed(ctx: ApiKeyContext, model: str) -> None:
    if not ctx.allowed_models:
        return
    if model not in ctx.allowed_models:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Model not allowed: {model}", "code": "model_forbidden"},
        )


def check_tool_permission(ctx: ApiKeyContext) -> None:
    if ctx.scopes.get("tools:execute") or ctx.role in {"admin", "developer"}:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Tool execution not permitted for this key", "code": "tool_forbidden"},
    )
