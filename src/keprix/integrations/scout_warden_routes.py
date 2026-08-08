"""Admin Scout Warden routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.integrations.scout_warden import ScoutWardenClient, scout_warden_enabled

router = APIRouter(prefix="/api/scout-warden", tags=["scout-warden"])


class ScanBody(BaseModel):
    target: str = Field(min_length=1)
    tenant_id: str = "local"


class AlertBody(BaseModel):
    id: str | None = None
    severity: str = "info"
    title: str = "Scout alert"
    summary: str = ""


@router.get("/status")
async def status(admin: dict = Depends(require_admin)) -> dict[str, Any]:
    from keprix.security.aiva_scout import KEPRIX_SENSORS, get_aiva_scout_guard

    guard = get_aiva_scout_guard()
    return {
        "enabled": scout_warden_enabled(),
        "keprix_target": "keprix-aiva",
        "monitored": True,
        "sensors": list(KEPRIX_SENSORS),
        "active_kills": guard.list_active_kills(),
    }


@router.post("/scans")
async def request_scan(body: ScanBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return await ScoutWardenClient().request_scan(target=body.target, tenant_id=body.tenant_id)


@router.post("/alerts")
async def ingest_alert(body: AlertBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return ScoutWardenClient().ingest_alert(body.model_dump())
