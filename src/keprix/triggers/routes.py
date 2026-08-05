"""HTTP API for the playbook trigger builder."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.triggers.engine import (
    approve_run,
    enqueue_event,
    process_runs,
    tick_and_process,
    tick_schedules,
)
from keprix.triggers.schedule import compute_next_run, iso_utc
from keprix.triggers.schema import Trigger, validate_trigger_input
from keprix.triggers.store import get_trigger_store, new_trigger_id

router = APIRouter(prefix="/api/triggers", tags=["triggers"])


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("email") or user.get("username") or "owner")


class TriggerCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    kind: Literal["schedule", "event"]
    schedule: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    action: dict[str, Any]
    timezone: str = "UTC"
    approval_mode: Literal["auto", "required", "notify"] = "auto"
    ai_mode: Literal["managed", "byok"] = "managed"
    workspace_id: str = "default"
    enabled: bool = True
    condition: dict[str, Any] | None = None
    note: str | None = None


class TriggerUpdateBody(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    schedule: dict[str, Any] | None = None
    event: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    timezone: str | None = None
    approval_mode: Literal["auto", "required", "notify"] | None = None
    ai_mode: Literal["managed", "byok"] | None = None
    condition: dict[str, Any] | None = None
    note: str | None = None


class EventIngressBody(BaseModel):
    source: str
    event_type: str
    payload: dict[str, Any] | None = None
    workspace_id: str | None = None


@router.get("")
async def list_triggers(
    workspace_id: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    items = get_trigger_store().list_triggers(workspace_id=workspace_id, enabled=enabled)
    return {"triggers": [t.to_dict() for t in items]}


@router.post("")
async def create_trigger(
    body: TriggerCreateBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        schedule, event, action = validate_trigger_input(
            kind=body.kind,
            schedule=body.schedule,
            event=body.event,
            action=body.action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    now = _utcnow()
    next_run = None
    if body.kind == "schedule" and schedule is not None:
        next_run = iso_utc(compute_next_run(schedule, timezone_name=body.timezone))

    trigger = Trigger(
        id=new_trigger_id(),
        workspace_id=body.workspace_id,
        owner_id=_user_id(user),
        name=body.name.strip(),
        enabled=body.enabled,
        kind=body.kind,
        schedule=schedule,
        timezone=body.timezone or "UTC",
        event=event,
        action=action,
        approval_mode=body.approval_mode,
        ai_mode=body.ai_mode,
        next_run_at=next_run,
        last_run_at=None,
        created_at=now,
        updated_at=now,
        condition=dict(body.condition or {}),
        note=body.note,
    )
    get_trigger_store().create_trigger(trigger)
    return {"trigger": trigger.to_dict()}


@router.get("/runs")
async def list_all_runs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    runs = get_trigger_store().list_runs(status=status, limit=limit)
    return {"runs": [r.to_dict() for r in runs]}


@router.post("/runs/{run_id}/approve")
async def approve_trigger_run(run_id: str, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    run = await approve_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found or not awaiting approval")
    return {"run": run.to_dict()}


@router.post("/events")
async def ingress_event(body: EventIngressBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    queued = enqueue_event(
        source=body.source,
        event_type=body.event_type,
        payload=body.payload,
        workspace_id=body.workspace_id,
    )
    return {"queued": queued}


@router.post("/tick")
async def tick(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return await tick_and_process()


@router.post("/process")
async def process(
    limit: int = Query(default=5, ge=1, le=50),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    return {"processed": await process_runs(limit=limit), "queued_schedules": tick_schedules()}


@router.get("/{trigger_id}")
async def get_trigger(trigger_id: str, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    trigger = get_trigger_store().get_trigger(trigger_id)
    if trigger is None:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"trigger": trigger.to_dict()}


@router.patch("/{trigger_id}")
async def update_trigger(
    trigger_id: str,
    body: TriggerUpdateBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    store = get_trigger_store()
    trigger = store.get_trigger(trigger_id)
    if trigger is None:
        raise HTTPException(status_code=404, detail="Trigger not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        trigger.name = str(data["name"]).strip()
    if "enabled" in data and data["enabled"] is not None:
        trigger.enabled = bool(data["enabled"])
    if "timezone" in data and data["timezone"]:
        trigger.timezone = str(data["timezone"])
    if "approval_mode" in data and data["approval_mode"]:
        trigger.approval_mode = data["approval_mode"]
    if "ai_mode" in data and data["ai_mode"]:
        trigger.ai_mode = data["ai_mode"]
    if "condition" in data and data["condition"] is not None:
        trigger.condition = dict(data["condition"] or {})
    if "note" in data:
        trigger.note = data["note"]
    try:
        if "action" in data and data["action"] is not None:
            _, _, action = validate_trigger_input(
                kind=trigger.kind,
                schedule=trigger.schedule.to_dict() if trigger.schedule else None,
                event=trigger.event.to_dict() if trigger.event else None,
                action=data["action"],
            )
            trigger.action = action
        if "schedule" in data and data["schedule"] is not None and trigger.kind == "schedule":
            schedule, _, _ = validate_trigger_input(
                kind="schedule",
                schedule=data["schedule"],
                event=None,
                action=trigger.action.to_dict(),
            )
            trigger.schedule = schedule
            trigger.next_run_at = iso_utc(
                compute_next_run(schedule, timezone_name=trigger.timezone)  # type: ignore[arg-type]
            )
        if "event" in data and data["event"] is not None and trigger.kind == "event":
            _, event, _ = validate_trigger_input(
                kind="event",
                schedule=None,
                event=data["event"],
                action=trigger.action.to_dict(),
            )
            trigger.event = event
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.update_trigger(trigger)
    return {"trigger": trigger.to_dict()}


@router.delete("/{trigger_id}")
async def delete_trigger(trigger_id: str, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    ok = get_trigger_store().delete_trigger(trigger_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"ok": True}


@router.post("/{trigger_id}/test")
async def test_trigger(trigger_id: str, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    store = get_trigger_store()
    trigger = store.get_trigger(trigger_id)
    if trigger is None:
        raise HTTPException(status_code=404, detail="Trigger not found")
    run = store.enqueue_run(trigger, payload={"test": True})
    processed = await process_runs(limit=1, store=store)
    latest = store.get_run(run.id)
    return {"run": latest.to_dict() if latest else run.to_dict(), "processed": processed}


@router.get("/{trigger_id}/runs")
async def list_trigger_runs(
    trigger_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _ = user
    if get_trigger_store().get_trigger(trigger_id) is None:
        raise HTTPException(status_code=404, detail="Trigger not found")
    runs = get_trigger_store().list_runs(trigger_id=trigger_id, limit=limit)
    return {"runs": [r.to_dict() for r in runs]}
