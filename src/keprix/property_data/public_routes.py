"""Versioned developer API for derived property data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query

from keprix.public_api.auth import check_api_path_allowed, require_api_key
from keprix.public_api.keys import ApiKeyContext
from keprix.property_data.api import epc, lookup, ownership, signals, sold_prices
from keprix.property_data.billing import require_property_entitlement

router = APIRouter(prefix="/api/property/v1", tags=["property-public-api"])


def _ctx(ctx: ApiKeyContext, path: str) -> None:
    check_api_path_allowed(ctx, path=path, method="GET")


@router.get("/lookup")
async def lookup_route(uprn: str = Query(default=""), postcode: str = Query(default=""), idempotency_key: str = Header(default="", alias="X-Idempotency-Key"), ctx: ApiKeyContext = Depends(require_api_key)):
    _ctx(ctx, "/api/property/v1/lookup")
    require_property_entitlement(ctx.workspace_id)
    return lookup(uprn=uprn, postcode=postcode, workspace_id=ctx.workspace_id, key_id=ctx.key_id, idempotency_key=idempotency_key)


@router.get("/sold-prices")
async def sold_prices_route(postcode: str, idempotency_key: str = Header(default="", alias="X-Idempotency-Key"), ctx: ApiKeyContext = Depends(require_api_key)):
    _ctx(ctx, "/api/property/v1/sold-prices")
    require_property_entitlement(ctx.workspace_id)
    return sold_prices(postcode=postcode, workspace_id=ctx.workspace_id, key_id=ctx.key_id, idempotency_key=idempotency_key)


@router.get("/epc")
async def epc_route(uprn: str, idempotency_key: str = Header(default="", alias="X-Idempotency-Key"), ctx: ApiKeyContext = Depends(require_api_key)):
    _ctx(ctx, "/api/property/v1/epc")
    require_property_entitlement(ctx.workspace_id)
    return epc(uprn=uprn, workspace_id=ctx.workspace_id, key_id=ctx.key_id, idempotency_key=idempotency_key)


@router.get("/ownership")
async def ownership_route(uprn: str, idempotency_key: str = Header(default="", alias="X-Idempotency-Key"), ctx: ApiKeyContext = Depends(require_api_key)):
    _ctx(ctx, "/api/property/v1/ownership")
    require_property_entitlement(ctx.workspace_id)
    return ownership(uprn=uprn, workspace_id=ctx.workspace_id, key_id=ctx.key_id, idempotency_key=idempotency_key)


@router.get("/signals")
async def signals_route(uprn: str, idempotency_key: str = Header(default="", alias="X-Idempotency-Key"), ctx: ApiKeyContext = Depends(require_api_key)):
    _ctx(ctx, "/api/property/v1/signals")
    require_property_entitlement(ctx.workspace_id)
    return signals(uprn=uprn, workspace_id=ctx.workspace_id, key_id=ctx.key_id, idempotency_key=idempotency_key)
