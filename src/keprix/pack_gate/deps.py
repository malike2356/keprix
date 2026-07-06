"""Pack gate API dependencies."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from keprix.api.auth import optional_user
from keprix.auth.config import auth_enabled
from keprix.auth.dependencies import get_current_user

_bearer = HTTPBearer(auto_error=False)

DEFAULT_WORKSPACE_ID = "default"


def resolve_workspace_id(request: Request) -> str:
    header = request.headers.get("X-Keprix-Workspace-Id") or request.headers.get("x-keprix-workspace-id")
    if header and header.strip():
        return header.strip()
    query = request.query_params.get("workspace_id")
    if query and query.strip():
        return query.strip()
    return os.environ.get("KEPRIX_WORKSPACE_ID", DEFAULT_WORKSPACE_ID)


async def get_pack_gate_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if auth_enabled():
        try:
            return get_current_user(request, credentials)
        except HTTPException:
            pass
    token_user = await optional_user(request, credentials)
    if token_user in {"admin", "developer", "api-user"}:
        return {"id": token_user, "username": token_user, "role": "admin"}
    if token_user:
        return {"id": token_user, "username": token_user, "role": "user"}
    return {"id": "local", "username": "local", "role": "admin"}


def require_workspace_admin(user: dict = Depends(get_pack_gate_actor)) -> dict:
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
