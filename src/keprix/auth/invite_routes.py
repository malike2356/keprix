"""Public workspace invite accept routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.user_invites import InviteError, accept_workspace_invite, get_invite_preview
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth/invites", tags=["auth-invites"])


class AcceptInviteRequest(BaseModel):
    token: str = Field(..., min_length=8)
    password: str = Field(..., min_length=8)
    username: str | None = None


@router.get("/{token}")
async def preview_invite(token: str) -> dict[str, Any]:
    try:
        return {"invite": get_invite_preview(token)}
    except InviteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/accept")
async def accept_invite(body: AcceptInviteRequest, request: Request) -> dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limit("auth_invite_accept", client_ip, limit=10, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many attempts", headers={"Retry-After": "3600"})
    try:
        result = await accept_workspace_invite(body.token, body.password, username=body.username)
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log("workspace_invite_accepted", user_id=result["user"].get("id"), ip_address=client_ip)
    return result
