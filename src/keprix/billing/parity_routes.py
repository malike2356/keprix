"""Billing promo and BYOK admin routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from keprix.auth.dependencies import require_admin
from keprix.billing.promo import get_promo_store
from keprix.billing.tenant_byok import get_byok_store
from keprix.billing.business_lines import (
    business_line_status,
    create_workspace_business_line,
    delete_workspace_business_line,
    list_workspace_business_lines,
)
from keprix.auth.dependencies import get_current_user
from keprix.billing.grandfathering import grant_feature_grandfather, list_feature_grandfather

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


class BusinessLineBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class GrandfatherBody(BaseModel):
    workspace_id: str = Field(min_length=1)
    feature: str = Field(min_length=1)
    reason: str = Field(min_length=1)


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


def _user_id(user: dict[str, Any]) -> str:
    return str(user.get("id") or user.get("username") or "default")


@router.get("/business-lines/status")
async def business_lines_status(workspace_id: str = Query(default="default"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return await business_line_status(workspace_id, _user_id(user))


@router.get("/business-lines")
async def business_lines(workspace_id: str = Query(default="default"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    rows = list_workspace_business_lines(workspace_id)
    return {"items": rows, "count": len(rows), "status": await business_line_status(workspace_id, _user_id(user))}


@router.post("/business-lines", status_code=201)
async def add_business_line(body: BusinessLineBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"business_line": await create_workspace_business_line(body.workspace_id, _user_id(user), body.name)}


@router.delete("/business-lines/{line_id}")
async def remove_business_line(line_id: str, workspace_id: str = Query(default="default"), user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _ = user
    if not delete_workspace_business_line(workspace_id, line_id):
        raise HTTPException(status_code=404, detail="business_line_not_found")
    return {"ok": True}


@router.post("/grandfather", status_code=201)
async def grant_grandfather(body: GrandfatherBody, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = admin
    try:
        created = grant_feature_grandfather(body.workspace_id, body.feature, body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"created": created, "items": list_feature_grandfather(body.workspace_id)}


@router.get("/grandfather/{workspace_id}")
async def get_grandfather(workspace_id: str, admin: dict = Depends(require_admin)) -> dict[str, Any]:
    _ = admin
    return {"items": list_feature_grandfather(workspace_id)}
