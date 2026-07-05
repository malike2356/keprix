"""Disabled legacy Aiva Scout provisioning API.

This code is kept only as historical reference. keys.petraclus.uk must not mount
or use Aiva workspace provisioning routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.scout_provision import provision_aiva_scout_workspace

router = APIRouter(prefix="/api/v1/scout", tags=["scout"])


class ProvisionRequest(BaseModel):
    product: str = "carina-aiva"
    account_email: EmailStr
    tier: str = "starter"
    aiva_workspace_id: str


@router.post("/workspaces/provision")
async def provision_workspace(body: ProvisionRequest) -> dict:
    if body.product != "carina-aiva":
        raise HTTPException(status_code=400, detail="Only carina-aiva provisioning is supported")

    result = await provision_aiva_scout_workspace(
        account_email=body.account_email,
        aiva_workspace_id=body.aiva_workspace_id,
        tier=body.tier,
    )
    if not result:
        raise HTTPException(status_code=502, detail="Scout provisioning failed")

    return {
        "workspace_id": result["scout_account_id"],
        "api_key": result["api_key"],
        "dashboard_url": result["dashboard_url"],
    }
