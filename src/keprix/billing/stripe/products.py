"""Map billing.yaml plans to existing Stripe price IDs.

Never create Stripe products or prices. Operators pin IDs from their own
`KEPRIX_STRIPE_CREDENTIALS_FILE` catalog into `billing.yaml`.
"""

from __future__ import annotations

from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.schema import BillingConfig, PlanConfig
from keprix.billing.store import get_billing_store


def _price_key(plan_id: str, amount: int, currency: str, interval: str | None) -> str:
    return f"{plan_id}:{amount}:{currency}:{interval or 'once'}"


async def sync_products_and_prices(config: BillingConfig | None = None) -> dict[str, Any]:
    """Pin existing Stripe price IDs from billing.yaml into the local map.

    Does not call Stripe to create products or prices.
    """
    cfg = config or load_billing_config()
    if cfg is None:
        return {"synced": False, "reason": "no billing config"}

    store = get_billing_store()
    stripe_map = await store.get_stripe_map()
    products = dict(stripe_map.get("products") or {})
    prices = dict(stripe_map.get("prices") or {})
    missing: list[str] = []

    for plan in cfg.plans:
        product_key = f"{cfg.product.id}:{plan.id}"
        products.setdefault(product_key, f"local_{cfg.product.id}_{plan.id}")
        for price_cfg in plan.resolved_prices():
            if int(price_cfg.amount or 0) == 0:
                continue
            key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
            if price_cfg.stripe_price_id:
                prices[key] = price_cfg.stripe_price_id
            elif key not in prices:
                missing.append(key)

    for addon in cfg.addons:
        product_key = f"{cfg.product.id}:addon:{addon.id}"
        products.setdefault(product_key, f"local_{cfg.product.id}_addon_{addon.id}")
        key = _price_key(addon.id, addon.price, addon.currency, addon.interval)
        if addon.stripe_price_id:
            prices[key] = addon.stripe_price_id
        elif key not in prices:
            missing.append(key)

    for donation in cfg.donations:
        # Open-amount coffee checkout uses Stripe price_data; a catalog pin is optional.
        if not donation.stripe_price_id:
            continue
        key = _price_key(f"donation:{donation.id}", donation.amount, donation.currency, None)
        prices[key] = donation.stripe_price_id

    await store.save_stripe_map({"products": products, "prices": prices})
    return {
        "synced": len(missing) == 0,
        "product_id": cfg.product.id,
        "plans": len(cfg.plans),
        "addons": len(cfg.addons),
        "donations": len(cfg.donations),
        "missing_price_ids": missing,
        "created_prices": False,
    }


async def resolve_price_id(plan: PlanConfig, *, interval: str | None = None, currency: str = "gbp") -> str | None:
    """Resolve a plan interval to a pinned Stripe price ID."""
    candidates = plan.resolved_prices()
    if interval:
        matched = [p for p in candidates if p.interval == interval and p.currency == currency]
        if matched:
            candidates = matched
    else:
        candidates = [p for p in candidates if p.currency == currency] or candidates

    for price_cfg in candidates:
        if price_cfg.stripe_price_id:
            return price_cfg.stripe_price_id

    cfg = load_billing_config()
    if cfg is None:
        return None
    store = get_billing_store()
    stripe_map = await store.get_stripe_map()
    prices = stripe_map.get("prices") or {}
    for price_cfg in candidates:
        key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
        if key in prices:
            return prices[key]
    for price_cfg in plan.resolved_prices():
        key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
        if key in prices:
            return prices[key]
    return None
