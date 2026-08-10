"""HTTP routes for public status snapshot and ops incident controls."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.status_page import (
    get_notification_log,
    get_store,
    maintenance_calendar,
    notify_active_users,
    run_health_cycle,
    schedule_maintenance,
)

router = APIRouter(prefix="/api/status", tags=["status"])


class IncidentBody(BaseModel):
    title: str = Field(min_length=1)
    affectedServices: list[str] = Field(default_factory=list)
    severity: Literal["minor", "major", "critical"] = "major"
    message: str | None = None


class IncidentUpdateBody(BaseModel):
    phase: Literal["investigating", "identified", "monitoring", "resolved"]
    message: str = Field(min_length=1)


class MaintenanceBody(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""
    affectedServices: list[str] = Field(default_factory=list)
    startsAt: str
    endsAt: str
    emergency: bool = False


class TickBody(BaseModel):
    notify: bool = False
    activeUsers: list[str] = Field(default_factory=list)
    subscribers: list[str] = Field(default_factory=list)


@router.get("/public")
async def public_snapshot() -> dict[str, Any]:
    return {"ok": True, "snapshot": get_store().snapshot()}


@router.get("")
async def admin_snapshot(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {
        "ok": True,
        "snapshot": get_store().snapshot(),
        "notifications": get_notification_log().records[:50],
    }


@router.post("/tick")
async def tick(body: TickBody | None = None, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    payload = body or TickBody()
    result = run_health_cycle(get_store())
    if result.get("created") and payload.notify:
        notify_active_users(result["created"], payload.activeUsers, log=get_notification_log())
    return {"ok": True, **result}


@router.post("/incidents")
async def create_incident(body: IncidentBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    incident = get_store().create_incident(
        title=body.title,
        affected_services=body.affectedServices,
        severity=body.severity,
        auto_created=False,
        message=body.message,
    )
    return {"ok": True, "incident": incident}


@router.post("/incidents/{incident_id}/update")
async def update_incident(
    incident_id: str,
    body: IncidentUpdateBody,
    user: dict = Depends(require_admin),
) -> dict[str, Any]:
    _ = user
    incident = get_store().add_incident_update(incident_id, body.phase, body.message)
    if not incident:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True, "incident": incident}


@router.post("/maintenance")
async def create_maintenance(body: MaintenanceBody, user: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = user
    try:
        window = schedule_maintenance(
            get_store(),
            title=body.title,
            description=body.description,
            affected_services=body.affectedServices,
            starts_at=body.startsAt,
            ends_at=body.endsAt,
            emergency=body.emergency,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "maintenance": window}


@router.get("/maintenance")
async def list_maintenance(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    return {"ok": True, "maintenance": maintenance_calendar(get_store())}
