"""IsolationMiddleware: set ProductContext on every incoming request."""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response, JSONResponse
    _STARLETTE = True
except ImportError:
    _STARLETTE = False

from .product_context import ProductContext, clear_product_context, set_product_context
from .isolation_violation import IsolationViolation

_KNOWN_PRODUCTS = frozenset({"aiva", "abbis", "petraclus", "fleetz", "nhs", "keprix"})


def _resolve_request_user(request: "Request") -> dict[str, Any] | None:
    """Best-effort auth resolution for middleware (before Depends runs)."""
    existing = getattr(request.state, "user", None)
    if isinstance(existing, dict):
        return existing
    try:
        from keprix.auth.config import auth_enabled
        from keprix.auth.session import auth_manager

        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            token = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
        if not token:
            token = request.cookies.get("keprix_session")
        if token and token.startswith("kp_"):
            # API key identity: treat workspace claim as user id for membership lookups.
            return {"id": "api-key", "username": "api-key", "role": "member"}
        if token:
            user = auth_manager.validate_token(token)
            if user:
                request.state.user = user
                return user
        if not auth_enabled():
            user = auth_manager.guest_user()
            request.state.user = user
            return user
    except Exception as exc:
        logger.debug("IsolationMiddleware user resolve skipped: %s", exc)
    return None


def _build_context(request: "Request") -> ProductContext:
    """Extract product, workspace, and tenant from request headers and session."""
    headers = request.headers

    product_id = headers.get("X-Keprix-Product", "keprix").lower()
    if product_id not in _KNOWN_PRODUCTS:
        product_id = "keprix"

    workspace_id = (
        headers.get("X-Keprix-Workspace")
        or request.path_params.get("workspace_id")
        or headers.get("X-Workspace-Id")
        or ""
    )

    header_tenant = headers.get("X-Keprix-Tenant") or None
    session_id = headers.get("X-Keprix-Session") or None

    raw_scopes = headers.get("X-Keprix-Scopes", "")
    scopes = frozenset(s for s in raw_scopes.split() if s)

    user = _resolve_request_user(request)
    try:
        from keprix.tenancy.resolve import resolve_tenant_id

        tenant_id = resolve_tenant_id(
            header_ref=header_tenant,
            user=user if isinstance(user, dict) else None,
            host=headers.get("host"),
        )
    except Exception:
        tenant_id = header_tenant

    if not workspace_id and tenant_id:
        workspace_id = tenant_id

    return ProductContext(
        product_id=product_id,
        workspace_id=workspace_id,
        tenant_id=tenant_id,
        session_id=session_id,
        scopes=scopes,
    )


if _STARLETTE:
    class IsolationMiddleware(BaseHTTPMiddleware):
        """Set ProductContext on every request and clear it after."""

        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            ctx = _build_context(request)
            token = set_product_context(ctx)
            try:
                response = await call_next(request)
                return response
            except IsolationViolation:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied"},
                )
            finally:
                clear_product_context(token)
else:
    class IsolationMiddleware:  # type: ignore[no-redef]
        """Unavailable without Starlette."""
