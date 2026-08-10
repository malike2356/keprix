"""Legal acceptance gate middleware."""

from __future__ import annotations

import hashlib
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from keprix.legal.policy_store import get_active_policies
from keprix.legal.store import get_acceptance_store

EXEMPT_PREFIXES = (
    "/api/legal/",
    "/api/health",
    "/api/auth/",
    "/api/v1/auth/",
    "/api/discovery/",
    "/api/product-schema.json",
    "/api/transparency/",
    "/legal/",
    "/review/",
    "/api/governance/webhook",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/productSpec.json",
    "/install.json",
    "/llms.txt",
    "/ai.txt",
    "/.well-known/",
)


def requires_legal_check(path: str) -> bool:
    if os.environ.get("KEPRIX_LEGAL_GATE", "1") == "0":
        return False
    if not path.startswith("/api/"):
        return False
    return not any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def _user_id(request: Request) -> str | None:
    header = request.headers.get("x-user-id", "").strip()
    if header:
        return header
    if getattr(request.state, "user", None):
        return str(request.state.user)
    return None


def pending_policies(workspace_id: str, user_id: str) -> list[dict[str, str]]:
    store = get_acceptance_store()
    pending: list[dict[str, str]] = []
    for policy in get_active_policies():
        if not store.has_accepted(
            workspace_id=workspace_id,
            user_id=user_id,
            policy_type=policy.policy_type,
            policy_version=policy.version,
        ):
            pending.append(
                {
                    "policy_type": policy.policy_type,
                    "version": policy.version,
                    "title": policy.title,
                }
            )
    return pending


def hash_user_agent(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LegalGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not requires_legal_check(request.url.path):
            return await call_next(request)
        user_id = _user_id(request)
        if not user_id:
            return await call_next(request)
        workspace_id = request.headers.get("x-workspace-id", "default").strip() or "default"
        missing = pending_policies(workspace_id, user_id)
        if missing:
            return JSONResponse(
                status_code=451,
                content={
                    "error": "legal_acceptance_required",
                    "message": "You must accept the current policies before continuing.",
                    "pending_policies": [row["policy_type"] for row in missing],
                    "accept_url": "/legal/accept",
                    "policies": missing,
                },
            )
        return await call_next(request)
