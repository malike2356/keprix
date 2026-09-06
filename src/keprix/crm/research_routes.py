"""Authenticated deep-research enrichment routes (prompt 02)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.research_enrich import research_lead, research_leads_batch
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/research", tags=["crm-research"])


class ResearchBatchBody(BaseModel):
    lead_ids: list[str]


@router.post("/{lead_id}")
async def research_single(
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
    result = await research_lead(store, workspace, lead_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error", "not found"))
    return result


@router.post("/batch")
async def research_batch(
    body: ResearchBatchBody,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    workspace = _workspace(workspace_id, x_workspace_id, user)
    if not body.lead_ids:
        raise HTTPException(status_code=422, detail="lead_ids is required")
    if len(body.lead_ids) > 500:
        raise HTTPException(status_code=422, detail="lead_ids exceeds 500")
    return await research_leads_batch(store, workspace, body.lead_ids)
