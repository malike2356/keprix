"""Four C's maturity audit API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.agent_os.maturity_audit_service import MaturityAuditService
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os/maturity", tags=["agent-os"])


class RunBody(BaseModel):
    workspace_id: str | None = "personal-os"
    workspace_path: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.post("/run")
async def run_maturity(body: RunBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    result = MaturityAuditService().run(workspace_id=body.workspace_id, workspace_path=body.workspace_path)
    record_onboarding_event_for_user(user, "maturity_audit.completed")
    return {"audit": result.to_dict()}


@router.get("")
async def list_maturity(limit: int = 50, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    return {"audits": [audit.to_dict() for audit in MaturityAuditService().list(limit=limit)]}


@router.get("/{audit_id}")
async def get_maturity(audit_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    result = MaturityAuditService().get(audit_id)
    if result is None:
        raise HTTPException(status_code=404, detail="maturity audit not found")
    return {"audit": result.to_dict()}


@router.post("/{audit_id}/export-to-level-up")
async def export_maturity(audit_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    try:
        return MaturityAuditService().export_to_level_up(audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="maturity audit not found") from exc
