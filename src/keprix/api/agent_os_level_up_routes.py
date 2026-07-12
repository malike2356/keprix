"""Agent OS level-up remediation API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.level_up_service import LevelUpService
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os/level-up", tags=["agent-os"])


class GenerateBody(BaseModel):
    audit_id: str = Field(..., min_length=1)
    workspace_path: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.post("/generate")
async def generate_level_up(body: GenerateBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    try:
        plan = LevelUpService().generate(audit_id=body.audit_id, workspace_path=body.workspace_path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="maturity audit not found") from exc
    return {"plan": plan.to_dict()}


@router.get("/{plan_id}")
async def get_level_up(plan_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    plan = LevelUpService().get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="level-up plan not found")
    return {"plan": plan.to_dict()}


@router.post("/{plan_id}/actions/{action_id}/complete")
async def complete_level_up_action(plan_id: str, action_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        plan = LevelUpService().complete_action(plan_id, action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="level-up action not found") from exc
    record_onboarding_event_for_user(user, "level_up.action_completed")
    return {"plan": plan.to_dict()}


@router.post("/{plan_id}/apply-safe-stubs")
async def apply_level_up_stubs(plan_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    try:
        return LevelUpService().apply_safe_stubs(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="level-up plan not found") from exc


@router.post("/{plan_id}/re-audit")
async def re_audit_level_up(plan_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    _guard_enabled()
    try:
        return LevelUpService().re_audit(plan_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="level-up plan not found") from exc
