"""OSINT enrichment routes (prompt 05). Disabled by default; opt-in + lawful-use gate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.osint_enrich import osint_enrich_lead
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/osint", tags=["crm-osint"])


class BatchBody(BaseModel):
    lead_ids: list[str]


@router.post("/{lead_id}")
async def osint_single(
    lead_id: str,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    workspace = _workspace(workspace_id, x_workspace_id, user)
    if not store.get_lead(workspace, lead_id):
        raise HTTPException(status_code=404, detail="lead not found")
    return await osint_enrich_lead(store, workspace, lead_id)


@router.post("/batch")
async def osint_batch(
    body: BatchBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    workspace = _workspace(workspace_id, x_workspace_id, user)
    if not body.lead_ids:
        raise HTTPException(status_code=422, detail="lead_ids is required")
    if len(body.lead_ids) > 50:
        raise HTTPException(status_code=422, detail="lead_ids exceeds 50")
    results = []
    for lead_id in body.lead_ids:
        if not store.get_lead(workspace, lead_id):
            results.append({"lead_id": lead_id, "status": "skipped"})
            continue
        results.append(await osint_enrich_lead(store, workspace, lead_id))
    return {"ok": True, "results": results}
