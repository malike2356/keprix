"""Agent OS Action Board configuration routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.agent_os.action_board_store import ActionBoardConfig, ActionBoardStore, ActionPin
from keprix.agent_os.onboarding_events import record_onboarding_event_for_user
from keprix.agent_os.skill_scheduler import SkillScheduler
from keprix.agent_os.workflow_audit_service import agent_os_enabled
from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/agent-os", tags=["agent-os"])


class PinBody(BaseModel):
    type: str = Field(..., pattern="^(skill|playbook|agent_app)$")
    id: str = Field(..., min_length=1)
    label: str | None = None
    shortcut: str | None = None


class BoardBody(BaseModel):
    pins: list[PinBody] = Field(default_factory=list)
    shortcuts: dict[str, str] = Field(default_factory=dict)


class ScheduleBody(BaseModel):
    skill_slug: str = Field(..., min_length=1)
    schedule: str = Field(..., min_length=1)
    name: str | None = None
    deliver_to: str = "local"


def _guard_enabled() -> None:
    if not agent_os_enabled():
        raise HTTPException(status_code=403, detail="Agent OS is disabled")


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


@router.get("/board")
async def get_board(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    store = ActionBoardStore()
    return {
        "config": store.load(_user_id(user)).to_dict(),
        "actions": store.all_actions(),
        "metrics": store.metrics(),
        "links": {
            "chat": "/chat",
            "documents": "/documents",
            "playbooks_studio": "/playbooks/studio/new",
            "cron": "/admin/cron",
        },
    }


@router.put("/board")
async def save_board(body: BoardBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    store = ActionBoardStore()
    config = ActionBoardConfig(
        user_id=_user_id(user),
        pins=[
            ActionPin(
                type=pin.type,
                id=pin.id,
                label=pin.label or pin.id,
                shortcut=pin.shortcut,
            )
            for pin in body.pins
        ],
        shortcuts=body.shortcuts,
    )
    try:
        return {"config": store.save(config).to_dict()}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/board/pins")
async def add_pin(body: PinBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        config = ActionBoardStore().add_pin(
            _user_id(user),
            action_type=body.type,
            action_id=body.id,
            label=body.label,
            shortcut=body.shortcut,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "action_board.pin_added")
    return {"config": config.to_dict()}


@router.delete("/board/pins/{pin_id}")
async def remove_pin(pin_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    return {"config": ActionBoardStore().remove_pin(_user_id(user), pin_id).to_dict()}


@router.post("/board/schedule")
async def schedule_pin(body: ScheduleBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    try:
        result = SkillScheduler().schedule_skill(
            body.skill_slug,
            schedule=body.schedule,
            name=body.name,
            deliver_to=body.deliver_to,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_onboarding_event_for_user(user, "cron.created_from_skill")
    return result
