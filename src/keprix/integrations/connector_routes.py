"""HTTP API for the Integrations marketplace."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from keprix.integrations.connector_catalog import (
    catalog_install_status,
    connector_categories,
    get_connector,
    install_connector,
    load_connector_catalog,
)
from keprix.licensing.edition import feature_enabled
from keprix.integrations.governance_routes import request_connector_install, GovernanceRequest

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class InstallConnectorRequest(BaseModel):
    confirm: bool = False


@router.get("/catalog")
async def list_connectors(
    category: str | None = None,
    featured: bool | None = None,
    q: str | None = None,
    installed: bool | None = None,
    workspace_id: str = "default",
) -> dict[str, Any]:
    query = (q or "").strip().lower()
    connectors = []
    for entry in load_connector_catalog():
        status = catalog_install_status(entry.id, workspace_id=workspace_id)
        if category and entry.category != category:
            continue
        if featured is not None and entry.featured != featured:
            continue
        if installed is not None and bool(status.get("installed")) != installed:
            continue
        haystack = " ".join([entry.id, entry.label, entry.description, " ".join(entry.tags)]).lower()
        if query and query not in haystack:
            continue
        connectors.append({"connector": entry.to_dict(), "install_status": status})
    return {"connectors": connectors}


@router.get("/catalog/{connector_id}")
async def get_connector_detail(connector_id: str, workspace_id: str = "default") -> dict[str, Any]:
    entry = get_connector(connector_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {
        "connector": entry.to_dict(),
        "install_status": catalog_install_status(connector_id, workspace_id=workspace_id),
    }


@router.post("/catalog/{connector_id}/install")
async def install_connector_route(connector_id: str, body: InstallConnectorRequest) -> dict[str, Any]:
    del body
    if feature_enabled("connector_governance"):
        requested = await request_connector_install(GovernanceRequest(connector_id=connector_id))
        return {"ok": True, "status": "pending_approval", "request": requested["request"]}
    result = install_connector(connector_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Connector not found")
    if result.get("status") == "not_installable":
        raise HTTPException(status_code=501, detail="connector_not_installable")
    return result


@router.get("/categories")
async def list_connector_categories() -> dict[str, Any]:
    return {"categories": connector_categories()}
