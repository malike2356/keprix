"""Companies House auto-enrich routes (prompt 03)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.companies_house_enrich import enrich_leads_batch, match_company
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/enrich", tags=["crm-companies-house"])


class MatchBody(BaseModel):
    company_name: str
    town_city: str = ""


class BatchBody(BaseModel):
    lead_ids: list[str]


@router.post("/match")
async def match(
    body: MatchBody,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "view")
    result = await match_company(body.company_name, body.town_city)
    if result is None:
        return {"ok": True, "matched": False}
    return {"ok": True, "matched": True, **result}


@router.post("/batch")
async def batch(
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
    if len(body.lead_ids) > 500:
        raise HTTPException(status_code=422, detail="lead_ids exceeds 500")
    return await enrich_leads_batch(store, workspace, body.lead_ids)
