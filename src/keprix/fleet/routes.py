"""Fleet management HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user, require_admin
from keprix.fleet.manager import get_fleet_manager
from keprix.licensing.dependencies import enterprise_feature

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


class RegisterInstanceBody(BaseModel):
    name: str
    base_url: str
    version: str = "0.0.0"


class HealthReportBody(BaseModel):
    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    disk_pct: float = 0.0
    reachable: bool = True
    update_available: bool = False
    alerts: int = 0
    version: str | None = None


@router.get("/instances")
async def list_instances(
    _feature: None = Depends(enterprise_feature("fleet_deploy")),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return {"instances": get_fleet_manager().list_instances()}


@router.post("/instances")
async def register_instance(
    body: RegisterInstanceBody,
    _feature: None = Depends(enterprise_feature("fleet_deploy")),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    row = get_fleet_manager().register(name=body.name.strip(), base_url=body.base_url.strip(), version=body.version)
    return {"instance": row}


@router.post("/instances/{instance_id}/health")
async def report_health(
    instance_id: str,
    body: HealthReportBody,
    _feature: None = Depends(enterprise_feature("fleet_deploy")),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    row = get_fleet_manager().record_health(instance_id, metrics=body.model_dump())
    if row is None:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"instance": row}


@router.get("/audit")
async def fleet_audit(
    limit: int = 100,
    _feature: None = Depends(enterprise_feature("audit_export")),
    _admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    return {"events": get_fleet_manager().list_audit(limit=limit)}
