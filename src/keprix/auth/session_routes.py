"""Active session list and revoke routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from keprix.auth.dependencies import get_current_user
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log

router = APIRouter(prefix="/api/auth", tags=["auth-sessions"])


@router.get("/sessions")
async def list_active_sessions(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    token = getattr(request.state, "auth_token", None)
    sessions = auth_manager.list_sessions(str(user["id"]), current_token=token)
    return {"sessions": sessions}


@router.delete("/sessions/{session_id}")
async def revoke_active_session(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, bool]:
    token = getattr(request.state, "auth_token", None)
    removed = auth_manager.revoke_session(str(user["id"]), session_id, current_token=token)
    if not removed:
        raise HTTPException(status_code=404, detail="Session not found or cannot revoke current session")
    await audit_log(
        "session_revoked",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
        event_data={"session_id": session_id},
    )
    return {"ok": True}


@router.post("/sessions/revoke-others")
async def revoke_other_sessions(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, int]:
    token = getattr(request.state, "auth_token", None)
    removed = auth_manager.revoke_all_sessions(str(user["id"]), except_token=token)
    await audit_log(
        "sessions_revoked_all",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
        event_data={"removed": removed},
    )
    return {"removed": removed}
