"""Billing promo and BYOK admin routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.billing.promo import get_promo_store
from keprix.billing.tenant_byok import get_byok_store

router = APIRouter(prefix="/api/billing/parity", tags=["billing-parity"])


class PromoUpsertBody(BaseModel):
    code: str = Field(min_length=1)
    percent_off: int = 0
    trial_days: int = 0
    price_id: str | None = None


class PromoRedeemBody(BaseModel):
    code: str = Field(min_length=1)
    catalog_price_id: str | None = None


class ByokBody(BaseModel):
    tenant_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    api_key: str = Field(min_length=8)


@router.post("/promos")
async def upsert_promo(body: PromoUpsertBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    row = get_promo_store().upsert(
        body.code,
        percent_off=body.percent_off,
        trial_days=body.trial_days,
        price_id=body.price_id,
    )
    return {"promo": row}


@router.post("/promos/redeem")
async def redeem_promo(body: PromoRedeemBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    result = get_promo_store().redeem(body.code, catalog_price_id=body.catalog_price_id)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error") or "invalid_promo")
    return result


@router.post("/byok")
async def put_byok(body: ByokBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    try:
        meta = get_byok_store().put(tenant_id=body.tenant_id, provider=body.provider, api_key=body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"byok": meta}


@router.get("/byok/{tenant_id}")
async def list_byok(tenant_id: str, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    return {"keys": get_byok_store().public_status(tenant_id=tenant_id)}
