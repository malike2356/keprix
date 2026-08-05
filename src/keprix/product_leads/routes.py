"""Lead API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.product_leads.store import get_lead_store

router = APIRouter(prefix="/api/leads", tags=["product-leads"])


class CreateLeadBody(BaseModel):
    name: str = Field(min_length=1)
    email: str = ""
    contact_id: str | None = None
    campaign_id: str | None = None


class LinkBookingBody(BaseModel):
    booking_id: str = Field(min_length=1)


@router.get("")
async def list_leads(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = get_lead_store().list_leads()
    return {"leads": rows, "count": len(rows)}


@router.post("")
async def create_lead(body: CreateLeadBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    lead = get_lead_store().create(
        name=body.name,
        email=body.email,
        contact_id=body.contact_id,
        campaign_id=body.campaign_id,
    )
    return {"lead": lead}


@router.post("/{lead_id}/link-booking")
async def link_booking(
    lead_id: str,
    body: LinkBookingBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        lead = get_lead_store().link_booking(lead_id, body.booking_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Lead not found") from exc
    return {"lead": lead}
