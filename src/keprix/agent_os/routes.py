"""Agent OS workflow audit API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import WorkflowAuditService, agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class StartAuditBody(BaseModel):
    mode: str = Field(..., pattern="^(manual|session[_-]scan|interview)$")
    session_count: int = Field(default=10, ge=1, le=50)


class ManualTasksBody(BaseModel):
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class InterviewContinueBody(BaseModel):
    message: str = Field(..., min_length=1)


def _service() -> WorkflowAuditService:
    return WorkflowAuditService()


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _guard_owner(audit: Any, user: dict) -> None:
    owner = getattr(audit, "user_id", None)
    user_id = str(user.get("id") or user.get("user_id") or "")
    if owner and user_id and owner != user_id:
        raise HTTPException(status_code=404, detail="audit not found")


@router.post("/audit/start")
async def start_audit(
    body: StartAuditBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    try:
        audit = _service().start(body.mode, user, session_count=body.session_count)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"audit": audit.to_dict()}


@router.post("/audit/{audit_id}/continue")
async def continue_audit(
    audit_id: str,
    body: InterviewContinueBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    service = _service()
    audit = service.get(audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    _guard_owner(audit, user)
    if audit.mode == "interview":
        audit, reply, done = await service.continue_interview(audit_id, body.message)
        return {"audit": audit.to_dict(), "reply": reply, "done": done}
    raise HTTPException(status_code=400, detail="continue is only supported for interview audits")


@router.put("/audit/{audit_id}/tasks")
async def update_manual_tasks(
    audit_id: str,
    body: ManualTasksBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    audit = _service().get(audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    _guard_owner(audit, user)
    try:
        audit = _service().update_manual_tasks(audit_id, body.tasks)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="audit not found") from exc
    return {"audit": audit.to_dict()}


@router.post("/audit/{audit_id}/complete")
async def complete_audit(
    audit_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    _guard_enabled()
    existing = _service().get(audit_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="audit not found")
    _guard_owner(existing, user)
    try:
        audit = _service().complete(audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="audit not found") from exc
    record_onboarding_event_for_user(user, "audit.completed")
    return {"audit": audit.to_dict()}


@router.get("/audit/{audit_id}")
async def get_audit(audit_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    audit = _service().get(audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    _guard_owner(audit, user)
    return {"audit": audit.to_dict()}


@router.get("/audit")
@router.get("/audits")
async def list_audits(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    audits = _service().list_audits(user)
    return {"audits": [audit.to_dict() for audit in audits]}


@router.post("/audit/{audit_id}/export-to-proposals")
async def export_to_proposals(audit_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    audit = _service().get(audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="audit not found")
    _guard_owner(audit, user)
    try:
        count = _service().export_to_proposals(audit_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="audit not found") from exc
    return {"exported": count}
