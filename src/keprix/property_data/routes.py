"""Admin-owned property dataset status and refresh endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.property_data.refresh import dataset_status, refresh_all
from keprix.property_data.discovery import discover, get_config, set_config
from keprix.property_data.diligence import diligence_status, run_due_diligence
from keprix.property_data.saved_searches import (
    create_saved_search,
    list_saved_searches,
    propose_handoff,
    run_saved_search,
    update_match_status,
)
from keprix.property_data.billing import workspace_property_entitlement

router = APIRouter(prefix="/api/property", tags=["property-data"])


@router.get("/billing/status")
async def billing_status(workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    status = workspace_property_entitlement(workspace_id)
    from keprix.property_data.refresh import _connection
    connection = _connection()
    row = connection.execute("SELECT COALESCE(SUM(cost_tokens), 0), COUNT(*) FROM property_api_calls WHERE workspace_id=?", (workspace_id,)).fetchone()
    return {**status, "usage": {"calls": int(row[1] or 0), "cost_tokens": float(row[0] or 0)}}


@router.get("/domain-entitlement-limits")
async def domain_entitlement_limits(workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    """Return the same property gate used when a property discovery run starts."""
    return workspace_property_entitlement(workspace_id)


class DiscoveryConfigBody(BaseModel):
    enabled_signals: list[str] | None = None
    min_score: float = Field(default=0.5, ge=0, le=1)
    max_results: int = Field(default=50, ge=1, le=1000)
    region_filter: str = ""


class SavedSearchBody(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    criteria: dict[str, Any] = Field(default_factory=dict)
    run_schedule: str = "weekly"


class MatchStatusBody(BaseModel):
    status: str


class HandoffBody(BaseModel):
    match_id: str


@router.get("/data-layer/status")
async def status(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return dataset_status()


@router.post("/data-layer/refresh")
async def refresh(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return refresh_all()


@router.get("/discovery/config")
async def discovery_config(workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return get_config(workspace_id)


@router.put("/discovery/config")
async def update_discovery_config(body: DiscoveryConfigBody, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return set_config(workspace_id, body.model_dump(exclude_none=True))


@router.post("/discover")
async def discover_route(workspace_id: str = "default", materialize: bool = False, _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return discover(workspace_id, materialize=materialize)


@router.post("/due-diligence")
async def due_diligence(uprn: str = "", address: str = "", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    if not uprn and not address:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Provide uprn or address")
    return await run_due_diligence(uprn, address=address)


@router.get("/due-diligence/status")
async def due_diligence_status(_admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return diligence_status()


@router.get("/saved-searches")
async def saved_search_list(workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {"searches": list_saved_searches(workspace_id)}


@router.post("/saved-searches")
async def saved_search_create(body: SavedSearchBody, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {"search": create_saved_search(workspace_id, body.name, body.criteria, run_schedule=body.run_schedule)}


@router.delete("/saved-searches/{search_id}")
async def saved_search_delete(search_id: str, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    from keprix.property_data.refresh import _connection
    connection = _connection()
    changed = connection.execute("UPDATE property_saved_searches SET active=0 WHERE id=? AND workspace_id=?", (search_id, workspace_id)).rowcount
    connection.commit()
    return {"deleted": bool(changed), "id": search_id}


@router.post("/saved-searches/{search_id}/run")
async def saved_search_run(search_id: str, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return run_saved_search(search_id, workspace_id)


@router.patch("/saved-searches/matches/{match_id}")
async def saved_match_status(match_id: str, body: MatchStatusBody, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {"updated": update_match_status(match_id, workspace_id, body.status)}


@router.post("/deals/propose-handoff")
async def deal_propose_handoff(body: HandoffBody, workspace_id: str = "default", _admin: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return propose_handoff(body.match_id, workspace_id)
