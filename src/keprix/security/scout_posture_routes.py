"""Local Scout posture endpoint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from keprix.auth.dependencies import get_current_user
from keprix.security.scout_posture import current_posture
from keprix.security.scout_standing_orders import list_standing_orders, set_standing_order

router = APIRouter(prefix="/api/security", tags=["security"])


class StandingOrderBody(BaseModel):
    enabled: bool
    schedule_cron: str = "0 8 * * 1"


@router.get("/posture")
async def security_posture() -> dict[str, Any]:
    return current_posture()


@router.get("/standing-orders")
async def standing_orders(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user.get("role") not in {"admin", "owner", "developer"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"items": list_standing_orders()}


@router.put("/standing-orders/{kind}")
async def update_standing_order(kind: str, body: StandingOrderBody, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user.get("role") not in {"admin", "owner", "developer"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return set_standing_order(kind, enabled=body.enabled, schedule_cron=body.schedule_cron)
