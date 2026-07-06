"""Admin workspace wipe routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from keprix.auth.dependencies import require_admin
from keprix.security.audit import audit_log
from keprix.workspace.repository import workspace_repo

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/wipe")
async def wipe_workspace(
    confirm: bool = Query(False),
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to wipe workspace data")
    user_id = str(user.get("id") or user.get("username"))
    counts = workspace_repo.wipe_user_data(user_id)
    await audit_log(
        "workspace_wipe",
        user_id=user_id,
        event_data={"counts": counts},
        severity="warning",
    )
    return {"ok": True, "deleted": counts}
