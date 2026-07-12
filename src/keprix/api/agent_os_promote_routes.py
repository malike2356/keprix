"""Agent OS skill promotion routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.automation_promoter import AutomationPromoter
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class PromoteBody(BaseModel):
    skill_slug: str = Field(..., min_length=1)
    target: str = Field(..., pattern="^(cron|playbook|agent_app)$")
    schedule: str | None = None
    name: str | None = None
    deliver_to: str | None = None


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.post("/promote")
async def promote_skill(body: PromoteBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    try:
        result = AutomationPromoter().promote(**body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "automation.promoted")
    return result


@router.get("/links")
async def list_links(skill: str | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"links": AutomationPromoter().links_for_skill(skill) if skill else [link.to_dict() for link in AutomationPromoter().links.list()]}


@router.delete("/links/{automation_type}/{automation_id}")
async def remove_link(automation_type: str, automation_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    removed = AutomationPromoter().remove_link(automation_type, automation_id)
    return {"removed": removed}
