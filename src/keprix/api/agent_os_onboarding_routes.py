"""Agent OS onboarding checklist routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.onboarding_events import user_id_from_user
from keprix.agent_os.onboarding_progress import OnboardingProgressStore
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os/onboarding", tags=["agent-os"])


class CompleteStepBody(BaseModel):
    step_id: str = Field(..., min_length=1)


class DismissBody(BaseModel):
    dismissed: bool = True


class ResetBody(BaseModel):
    user_id: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _require_admin(user: dict[str, Any]) -> None:
    if str(user.get("role") or "user") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin role required")


@router.get("")
async def get_onboarding(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    payload = OnboardingProgressStore().load(user_id_from_user(user)).to_dict()
    from keprix.agent_os.milestones import build_milestones

    payload["milestones"] = build_milestones(user_id=user_id_from_user(user))
    return payload


@router.post("/complete-step")
async def complete_step(body: CompleteStepBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        progress = OnboardingProgressStore().complete_step(user_id_from_user(user), body.step_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="step not found") from exc
    return progress.to_dict()


@router.post("/complete-all")
async def complete_all(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    return OnboardingProgressStore().complete_all(user_id_from_user(user)).to_dict()


@router.post("/dismiss")
async def dismiss_onboarding(body: DismissBody = DismissBody(), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    return OnboardingProgressStore().dismiss(user_id_from_user(user), body.dismissed).to_dict()


@router.post("/reset")
async def reset_onboarding(body: ResetBody = ResetBody(), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    target_user_id = body.user_id or user_id_from_user(user)
    if target_user_id != user_id_from_user(user):
        _require_admin(user)
    return OnboardingProgressStore().reset(target_user_id).to_dict()
