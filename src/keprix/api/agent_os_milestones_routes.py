"""Day 1 / 7 / 30 milestone wizard API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.agent_os.milestones import build_milestones
from keprix.agent_os.onboarding_events import user_id_from_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


@router.get("/milestones")
async def get_milestones(
    user: dict = Depends(get_current_user),
    user_id: str | None = Query(default=None),
) -> dict[str, Any]:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")
    target = user_id or user_id_from_user(user)
    if user_id and user_id != user_id_from_user(user):
        if str(user.get("role") or "").lower() not in {"admin", "owner", "developer"}:
            raise HTTPException(status_code=403, detail="Admin role required")
    return build_milestones(user_id=target)
