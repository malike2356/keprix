"""Admin billing config: pin catalog Stripe prices onto plans via GUI."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.billing.config_loader import (
    load_billing_config,
    resolve_billing_config_write_path,
    save_billing_config,
)
from keprix.billing.schema import PlanPriceConfig
from keprix.billing.stripe.price_catalog import find_price_by_id, load_price_catalog
from keprix.billing.stripe.products import sync_products_and_prices

router = APIRouter(prefix="/api/billing/admin", tags=["billing-admin"])


def _require_billing_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class PlanPricePin(BaseModel):
    interval: Literal["month", "year"]
    stripe_price_id: str | None = None


class PlanPricingUpdate(BaseModel):
    id: str
    prices: list[PlanPricePin] = Field(default_factory=list)


class PricingUpdateBody(BaseModel):
    plans: list[PlanPricingUpdate]


@router.get("/catalog")
async def list_price_catalog(
    scope: str = "keprix",
    _admin: dict = Depends(_require_billing_admin),
) -> dict[str, Any]:
    """Return operator catalog prices for the billing admin dropdown.

    Default ``scope=keprix`` filters multi-product credential files so Scout,
    Carina, Aiva, and other non-Keprix sections are excluded.
    """
    resolved = scope.strip().lower() if scope else "keprix"
    if resolved not in {"keprix", "all"}:
        resolved = "keprix"
    entries = [
        {
            "label": entry.label,
            "price_id": entry.price_id,
            "amount": entry.amount,
            "currency": entry.currency,
            "interval": entry.interval,
            "section": entry.section,
        }
        for entry in load_price_catalog(scope=resolved)
        if entry.price_id.startswith("price_")
    ]
    return {"items": entries, "count": len(entries), "scope": resolved}


@router.get("/pricing")
async def get_plan_pricing(_admin: dict = Depends(_require_billing_admin)) -> dict[str, Any]:
    cfg = load_billing_config(force_reload=True)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Billing config not found")
    write_path = resolve_billing_config_write_path()
    return {
        "config_path": str(write_path),
        "product": cfg.product.model_dump(),
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "description": plan.description,
                "prices": [price.model_dump() for price in plan.resolved_prices()],
            }
            for plan in cfg.plans
        ],
    }


@router.put("/pricing")
async def update_plan_pricing(
    body: PricingUpdateBody,
    _admin: dict = Depends(_require_billing_admin),
) -> dict[str, Any]:
    cfg = load_billing_config(force_reload=True)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Billing config not found")

    by_id = {plan.id: plan for plan in cfg.plans}
    for update in body.plans:
        plan = by_id.get(update.id)
        if plan is None:
            raise HTTPException(status_code=400, detail=f"Unknown plan id: {update.id}")

        # Free / zero-amount plans stay free (no Stripe pin required).
        existing = plan.resolved_prices()
        if existing and all(int(p.amount or 0) == 0 for p in existing) and not any(
            pin.stripe_price_id for pin in update.prices
        ):
            continue

        next_prices: list[PlanPriceConfig] = []
        for pin in update.prices:
            price_id = (pin.stripe_price_id or "").strip()
            if not price_id:
                continue
            catalog = find_price_by_id(price_id)
            if catalog is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Price {price_id} is not in the operator Stripe catalog. "
                        "Add it to KEPRIX_STRIPE_CREDENTIALS_FILE (Keprix-relevant section) first."
                    ),
                )
            amount = catalog.amount
            if amount is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Catalog entry for {price_id} has no £ amount in its label",
                )
            interval = pin.interval
            if catalog.interval and catalog.interval != interval:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{price_id} is labeled as {catalog.interval}, "
                        f"but you selected {interval}"
                    ),
                )
            next_prices.append(
                PlanPriceConfig(
                    amount=amount,
                    currency=catalog.currency,
                    interval=interval,
                    stripe_price_id=price_id,
                    discount_text=None,
                )
            )

        if not next_prices and plan.id != "community":
            raise HTTPException(
                status_code=400,
                detail=f"Plan {plan.id} needs at least one catalog price pin",
            )

        # Preserve year discount_text when amount still looks discounted vs 12x month.
        month = next((p for p in next_prices if p.interval == "month"), None)
        year = next((p for p in next_prices if p.interval == "year"), None)
        if month and year and month.amount > 0:
            full = month.amount * 12
            if year.amount < full:
                saved = round((1 - (year.amount / full)) * 100)
                year.discount_text = f"Save {saved}%"

        plan.prices = next_prices
        plan.price = None
        plan.interval = None

    path = save_billing_config(cfg)
    sync = await sync_products_and_prices(cfg)
    return {
        "ok": True,
        "config_path": str(path),
        "sync": sync,
        "plans": [
            {
                "id": plan.id,
                "name": plan.name,
                "prices": [price.model_dump() for price in plan.resolved_prices()],
            }
            for plan in cfg.plans
        ],
    }
