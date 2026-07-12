"""Agent OS glass dashboard API (Prompt 270 Phase 3)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from keprix.agent_os.glass_dashboard import build_glass_dashboard
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user
from fastapi import HTTPException

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


@router.get("/glass")
async def agent_os_glass(
    days: int = Query(default=7, ge=1, le=90),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")
    return await build_glass_dashboard(days=days)
