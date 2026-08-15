"""Authenticated, opt-in CRM enrichment routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.crm.enrichment import apply_companies_house_profile
from keprix.crm.roles import require_cap
from keprix.crm.routes import _workspace
from keprix.crm.store import get_crm_store

router = APIRouter(prefix="/api/crm/leads", tags=["crm-enrichment"])


class CompaniesHouseEnrichBody(BaseModel):
    company_number: str | None = None


@router.post("/{lead_id}/enrich/companies-house")
async def enrich_companies_house(
    lead_id: str,
    body: CompaniesHouseEnrichBody | None = None,
    workspace_id: str | None = None,
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-Id"),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    require_cap(user, "edit")
    store = get_crm_store()
    workspace = _workspace(workspace_id, x_workspace_id, user)
    lead = store.get_lead(workspace, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")
    number = str((body.company_number if body else None) or lead.get("company_number") or "").strip().upper()
    if not number:
        raise HTTPException(status_code=422, detail="company_number is required on the lead or request")
    try:
        from keprix.integrations.companies_house.client import CompaniesHouseClient

        profile = await CompaniesHouseClient().get_company_profile(number, include_officers=True)
    except Exception as exc:  # provider-specific errors are returned without leaking credentials
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    updated = apply_companies_house_profile(store, workspace, lead_id, profile)
    return {"ok": True, "lead": updated, "provider": "companies_house", "source_url": profile.get("public_url")}
