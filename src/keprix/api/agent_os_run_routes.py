"""Agent OS headless run routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.headless_run_service import HeadlessRunService
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class RunBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


@router.post("/run/skill/{slug}")
async def run_skill(slug: str, body: RunBody | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        result = (await HeadlessRunService().run_skill(slug, (body.params if body else None))).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "headless_run.completed")
    return result


@router.post("/run/playbook/{playbook_id}")
async def run_playbook(playbook_id: str, body: RunBody | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        result = (await HeadlessRunService().run_playbook(playbook_id, (body.inputs if body else None))).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "headless_run.completed")
    return result


@router.post("/run/agent-app/{name}")
async def run_agent_app(name: str, body: RunBody | None = None, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        result = (await HeadlessRunService().run_agent_app(name, (body.inputs if body else None))).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "headless_run.completed")
    return result


@router.get("/run/{run_id}/status")
async def run_status(run_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    result = HeadlessRunService().status(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Headless run not found")
    return result.to_dict()
