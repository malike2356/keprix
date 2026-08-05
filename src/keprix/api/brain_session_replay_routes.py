"""Brain session replay API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import get_current_user
from keprix.brain.session_replay import SessionReplayService
from keprix.workspace.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/brain/sessions", tags=["brain-replay"])


def _workspace_id(workspace_id: str | None, user: dict[str, Any]) -> str:
    requested = workspace_id or str(user.get("workspace_id") or "default")
    allowed = user.get("workspace_id")
    if allowed and requested != allowed and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="workspace access denied")
    return requested


@router.get("")
async def list_brain_sessions(
    workspace_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    sessions = await SessionReplayService().list_sessions(user, resolved, limit=limit)
    return {"sessions": sessions}


@router.get("/{session_id}/replay")
async def session_replay(
    session_id: str,
    workspace_id: str | None = None,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    resolved = _workspace_id(workspace_id, user)
    try:
        data = await SessionReplayService().build(user, resolved, session_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    return data.to_dict()
