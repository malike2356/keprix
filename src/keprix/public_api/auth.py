"""Authentication for the public developer API."""

from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.auth.config import auth_enabled
from keprix.auth.session import auth_manager
from keprix.keys.local_access import effective_access_level
from keprix.public_api.keys import ApiKeyContext, get_api_key_store
from keprix.public_api.scopes_catalog import path_allowed_by_permissions

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.headers.get("x-api-key") or request.headers.get("X-API-Key")


def _client_ip(request: Request) -> str | None:
    from keprix.security.client_ip import client_ip

    value = client_ip(request, default="")
    return value or None


def _ip_allowed(ctx: ApiKeyContext, ip: str | None) -> bool:
    allow = [item.strip() for item in (ctx.allowed_ips or []) if item and item.strip()]
    if not allow:
        return True
    if not ip:
        return False
    return ip in allow or any(ip.startswith(prefix.rstrip("*")) for prefix in allow if prefix.endswith("*"))


def _env_token_context() -> ApiKeyContext:
    """Break-glass env token. Restricted unless explicitly widened."""
    unrestricted = os.environ.get("KEPRIX_API_TOKEN_UNRESTRICTED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    allow_tools = os.environ.get("KEPRIX_API_TOKEN_ALLOW_TOOLS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    scopes: dict = {}
    if allow_tools:
        scopes["tools:execute"] = True
        scopes["v1.tools"] = True
    if unrestricted:
        return ApiKeyContext(
            key_id="env-token",
            workspace_id="default",
            role="developer",
            allowed_models=[],
            allowed_endpoints=[],
            monthly_limit=None,
            usage_this_month=0,
            scopes=scopes or {"tools:execute": True},
            permissions={},
            restrict_key=False,
            allowed_ips=[],
            auto_disable_if_leaked=False,
            enabled=True,
            key_prefix="env-token",
        )
    return ApiKeyContext(
        key_id="env-token",
        workspace_id="default",
        role="api",
        allowed_models=["keprix"],
        allowed_endpoints=["/v1/chat/completions", "/v1/models"],
        monthly_limit=None,
        usage_this_month=0,
        scopes=scopes,
        permissions={"v1.chat": "access", "v1.models": "access"},
        restrict_key=True,
        allowed_ips=[],
        auto_disable_if_leaked=False,
        enabled=True,
        key_prefix="env-token",
    )


async def _enforce_token_security(request: Request, ctx: ApiKeyContext) -> None:
    """Fail closed: monitor/approval errors become 503, not silent allow."""
    from keprix.security.client_approval.fingerprint import build_client_fingerprint, hash_ip
    from keprix.security.client_approval.guard import enforce_client_approval
    from keprix.security.token_security.monitor import get_token_security_monitor

    monitor = get_token_security_monitor()
    if monitor.is_suspended(ctx.key_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "This API token is suspended pending owner review.",
                "code": "token_suspended",
                "token_id": ctx.key_id,
                "guidance": {
                    "what_to_do": "Unsuspend the token in Developer > Client approvals.",
                },
            },
        )

    await enforce_client_approval(
        request,
        token_id=ctx.key_id,
        workspace_id=ctx.workspace_id,
        scopes=ctx.scopes,
    )

    headers = {k: v for k, v in request.headers.items()}
    fp = build_client_fingerprint(
        user_agent=request.headers.get("user-agent"),
        ip=_client_ip(request),
        headers=headers,
        token_id=ctx.key_id,
    )
    result = monitor.observe_request(
        ctx.key_id,
        fingerprint=fp.fingerprint,
        ip_hash=fp.ip_hash or hash_ip(_client_ip(request)),
        ua_summary=fp.user_agent_summary,
    )
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "API token blocked by security monitor.",
                "code": result.reason or "token_security_blocked",
                "token_id": ctx.key_id,
                "suspended": result.suspended,
            },
        )


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ApiKeyContext:
    # Session cookies must never authenticate /v1 or other API-key surfaces.
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Missing API key", "code": "invalid_api_key"},
        )

    env_token = os.environ.get("KEPRIX_API_TOKEN", "")
    if env_token and token == env_token:
        ctx = _env_token_context()
        request.state.api_key = ctx
        request.state.auth_via = "env_api_token"
        return ctx

    ctx = get_api_key_store().authenticate(token)
    if ctx is None:
        try:
            from keprix.security.client_approval.fingerprint import hash_ip
            from keprix.security.token_security.monitor import get_token_security_monitor

            prefix = token[:12] if len(token) >= 8 else "invalid"
            get_token_security_monitor().record_failed_auth(prefix, ip_hash=hash_ip(_client_ip(request)))
        except Exception:
            logger.debug("failed-auth monitor skipped", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid API key", "code": "invalid_api_key"},
        )

    if not _ip_allowed(ctx, _client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Client IP not allowed for this API key", "code": "ip_forbidden"},
        )

    if ctx.monthly_limit is not None and ctx.usage_this_month >= ctx.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "Monthly usage limit exceeded", "code": "usage_limit_exceeded"},
        )

    try:
        await _enforce_token_security(request, ctx)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("token security subsystem failed closed for key %s", ctx.key_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "API key security checks unavailable; request denied.",
                "code": "security_unavailable",
            },
        ) from exc

    request.state.api_key = ctx
    request.state.auth_via = "api_key"
    return ctx


async def require_developer_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    admin_token = os.environ.get("KEPRIX_API_ADMIN_TOKEN", "")
    token = _extract_token(request, credentials)
    if admin_token and token == admin_token:
        return "admin"

    # Local machine owner (loopback + developer identity) may manage keys.
    client_host = (request.client.host if request.client else "") or ""
    is_loopback = client_host in {"127.0.0.1", "::1", "localhost"}
    if is_loopback and effective_access_level() == "developer":
        return "developer"

    # Auth disabled must NOT open key CRUD to the network.
    if not auth_enabled():
        if is_loopback:
            return "local"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Developer key management requires loopback or auth when AUTH_ENABLED is off",
                "code": "forbidden",
            },
        )

    if token and auth_manager.validate_token(token):
        return "session"
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Developer access required", "code": "forbidden"},
    )


def check_endpoint_allowed(ctx: ApiKeyContext, endpoint: str) -> None:
    if not ctx.restrict_key:
        return
    allowed = list(ctx.allowed_endpoints or [])
    if not allowed:
        _scope_violation(ctx, "endpoint", {"endpoint": endpoint, "reason": "empty_allowlist"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Endpoint not allowed: {endpoint}", "code": "endpoint_forbidden"},
        )
    if endpoint in allowed:
        return
    # Prefix match for versioned paths like /v1/tools/foo
    if any(endpoint == item or endpoint.startswith(item.rstrip("/") + "/") for item in allowed):
        return
    # Permission catalog path check (covers /api/* grants).
    if ctx.permissions and path_allowed_by_permissions(
        ctx.permissions,
        path=endpoint,
        method="GET",
    ):
        return
    _scope_violation(ctx, "endpoint", {"endpoint": endpoint})
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": f"Endpoint not allowed: {endpoint}", "code": "endpoint_forbidden"},
    )


def check_model_allowed(ctx: ApiKeyContext, model: str) -> None:
    if not ctx.restrict_key:
        return
    allowed = list(ctx.allowed_models or [])
    if not allowed:
        _scope_violation(ctx, "model", {"model": model, "reason": "empty_allowlist"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Model not allowed: {model}", "code": "model_forbidden"},
        )
    if model not in allowed:
        _scope_violation(ctx, "model", {"model": model})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": f"Model not allowed: {model}", "code": "model_forbidden"},
        )


def check_tool_permission(ctx: ApiKeyContext) -> None:
    # Role alone must never grant tools; require explicit scope.
    if ctx.scopes.get("tools:execute"):
        return
    if ctx.permissions.get("v1.tools") in {"access", "read", "write"}:
        return
    _scope_violation(ctx, "tools:execute")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "Tool execution not permitted for this API key", "code": "tool_forbidden"},
    )


def check_api_path_allowed(ctx: ApiKeyContext, *, path: str, method: str) -> None:
    """Enforce restricted-key permissions for arbitrary /api or /v1 paths."""
    if not ctx.restrict_key:
        return
    normalized = path.split("?", 1)[0]

    if normalized in (ctx.allowed_endpoints or []) or any(
        normalized == item or normalized.startswith(item.rstrip("/") + "/")
        for item in (ctx.allowed_endpoints or [])
    ):
        return

    if ctx.permissions and path_allowed_by_permissions(
        ctx.permissions,
        path=normalized,
        method=method,
    ):
        return

    _scope_violation(ctx, "endpoint", {"endpoint": normalized, "method": method})
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": f"API path not allowed for this key: {method} {normalized}",
            "code": "endpoint_forbidden",
        },
    )


def api_key_as_user(ctx: ApiKeyContext) -> dict:
    """Synthetic session user for API-key access to workspace /api/* routes."""
    role = "admin" if ctx.permissions.get("api.admin") in {"read", "write"} else "member"
    return {
        "id": f"apikey:{ctx.key_id}",
        "username": f"api-key:{ctx.key_prefix or ctx.key_id[:8]}",
        "role": role,
        "workspace_id": ctx.workspace_id,
        "auth_via": "api_key",
        "api_key_id": ctx.key_id,
        "api_key_scopes": ctx.scopes,
    }


def _scope_violation(ctx: ApiKeyContext, scope: str, detail: dict | None = None) -> None:
    try:
        from keprix.security.token_security.monitor import get_token_security_monitor

        get_token_security_monitor().record_scope_violation(
            ctx.key_id,
            scope=scope,
            detail=detail or {},
        )
    except Exception:
        logger.debug("scope violation audit skipped", exc_info=True)
