"""Sync billing.yaml plans to Stripe products and prices."""

from __future__ import annotations

from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.schema import BillingConfig, PlanConfig
from keprix.billing.store import get_billing_store
from keprix.billing.stripe.client import get_stripe_client


def _price_key(plan_id: str, amount: int, currency: str, interval: str | None) -> str:
    return f"{plan_id}:{amount}:{currency}:{interval or 'once'}"


async def sync_products_and_prices(config: BillingConfig | None = None) -> dict[str, Any]:
    cfg = config or load_billing_config()
    if cfg is None:
        return {"synced": False, "reason": "no billing config"}

    client = get_stripe_client()
    store = get_billing_store()
    stripe_map = await store.get_stripe_map()
    products = dict(stripe_map.get("products") or {})
    prices = dict(stripe_map.get("prices") or {})

    for plan in cfg.plans:
        product_key = f"{cfg.product.id}:{plan.id}"
        if product_key not in products:
            product = await client.create_product(
                name=f"{cfg.product.name} {plan.name}",
                metadata={"product_id": cfg.product.id, "plan_id": plan.id},
            )
            products[product_key] = product["id"]

        for price_cfg in plan.resolved_prices():
            key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
            if key in prices:
                continue
            created = await client.create_price(
                product_id=products[product_key],
                unit_amount=price_cfg.amount,
                currency=price_cfg.currency,
                interval=price_cfg.interval,
                metadata={"product_id": cfg.product.id, "plan_id": plan.id},
            )
            prices[key] = created["id"]

    for addon in cfg.addons:
        product_key = f"{cfg.product.id}:addon:{addon.id}"
        if product_key not in products:
            product = await client.create_product(
                name=f"{cfg.product.name} {addon.name}",
                metadata={"product_id": cfg.product.id, "addon_id": addon.id},
            )
            products[product_key] = product["id"]
        key = _price_key(addon.id, addon.price, addon.currency, addon.interval)
        if key not in prices:
            created = await client.create_price(
                product_id=products[product_key],
                unit_amount=addon.price,
                currency=addon.currency,
                interval=addon.interval,
                metadata={"product_id": cfg.product.id, "addon_id": addon.id},
            )
            prices[key] = created["id"]

    await store.save_stripe_map({"products": products, "prices": prices})
    return {
        "synced": True,
        "product_id": cfg.product.id,
        "plans": len(cfg.plans),
        "addons": len(cfg.addons),
        "mock_mode": client.mock_mode,
    }


async def resolve_price_id(plan: PlanConfig, *, interval: str | None = None, currency: str = "gbp") -> str | None:
    cfg = load_billing_config()
    if cfg is None:
        return None
    store = get_billing_store()
    stripe_map = await store.get_stripe_map()
    prices = stripe_map.get("prices") or {}
    for price_cfg in plan.resolved_prices():
        if interval and price_cfg.interval != interval:
            continue
        if price_cfg.currency != currency:
            continue
        key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
        return prices.get(key)
    for price_cfg in plan.resolved_prices():
        key = _price_key(plan.id, price_cfg.amount, price_cfg.currency, price_cfg.interval)
        if key in prices:
            return prices[key]
    return None
