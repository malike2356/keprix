"""HTTP routes for escalation queue (standalone Web UI + dashboard). Session auth."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from keprix.aiva_escalation.service import get_escalation_service
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/aiva/escalations", tags=["aiva-escalation"])


def _workspace(workspace_id: str | None, x_workspace_id: str | None) -> str:
    return (workspace_id or x_workspace_id or "default").strip() or "default"


@router.get("/queue")
async def get_queue(
    workspace_id: str | None = Query(default=None),
    status: str | None = Query("pending"),
    limit: int = Query(50, ge=1, le=200),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return get_escalation_service().get_queue(
        _workspace(workspace_id, x_workspace_id),
        status=status,
        limit=limit,
    )


@router.get("/{escalation_id}")
async def get_escalation(
    escalation_id: str,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    from keprix.aiva_escalation.store import get_escalation_store

    row = get_escalation_store().get_escalation(escalation_id)
    if not row:
        raise HTTPException(status_code=404, detail="escalation_not_found")
    return {"escalation": row}


@router.post("/{escalation_id}/assign")
async def assign_escalation(
    escalation_id: str,
    body: dict[str, Any],
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    assigned_va = str(body.get("assigned_va") or "").strip()
    if not assigned_va:
        raise HTTPException(status_code=422, detail="assigned_va is required")
    try:
        row = get_escalation_service().assign(escalation_id, assigned_va)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"escalation": row}


@router.post("/{escalation_id}/complete")
async def complete_escalation(
    escalation_id: str,
    body: dict[str, Any],
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    va_response = str(body.get("va_response") or "").strip()
    if not va_response:
        raise HTTPException(status_code=422, detail="va_response is required")
    try:
        row = get_escalation_service().complete(
            escalation_id,
            va_response,
            assigned_va=body.get("assigned_va"),
        )
    except (LookupError, ValueError) as exc:
        status = 404 if isinstance(exc, LookupError) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return {
        "escalation": row,
        "user_visible_response": row.get("va_response"),
    }


@router.post("/timeouts/process")
async def process_timeouts(
    body: dict[str, Any] | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    minutes = None
    if body and body.get("timeout_minutes") is not None:
        minutes = int(body["timeout_minutes"])
    return get_escalation_service().process_timeouts(timeout_minutes=minutes)
