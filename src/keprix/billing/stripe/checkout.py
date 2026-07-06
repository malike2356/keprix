"""Stripe Checkout session helpers."""

from __future__ import annotations

import os
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.stripe.client import get_stripe_client
from keprix.billing.stripe.products import resolve_price_id


async def create_checkout_session(
    *,
    user_id: str,
    email: str,
    plan_id: str,
    interval: str | None = "month",
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    cfg = load_billing_config()
    if cfg is None:
        raise RuntimeError("Billing is not configured")

    plan = cfg.plan_by_id(plan_id)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_id}")

    price_id = await resolve_price_id(plan, interval=interval)
    if price_id is None:
        raise ValueError(f"No Stripe price mapped for plan {plan_id}")

    store = get_billing_store()
    customer = await store.get_customer(user_id)
    stripe_customer_id = customer.get("stripe_customer_id") if customer else None
    if not stripe_customer_id:
        created = await get_stripe_client().create_customer(
            email=email,
            metadata={"user_id": user_id, "product_id": cfg.product.id},
        )
        stripe_customer_id = created["id"]
        await store.save_customer(
            user_id,
            {"email": email, "stripe_customer_id": stripe_customer_id, "product_id": cfg.product.id},
        )

    base_url = os.environ.get("KEPRIX_INSTANCE_URL", "http://localhost:3000").rstrip("/")
    session = await get_stripe_client().create_checkout_session(
        customer_id=stripe_customer_id,
        price_id=price_id,
        success_url=success_url or f"{base_url}/settings/billing?checkout=success",
        cancel_url=cancel_url or f"{base_url}/settings/billing?checkout=cancel",
        trial_days=cfg.product.trial_days,
        metadata={"user_id": user_id, "plan_id": plan_id, "product_id": cfg.product.id},
    )
    return {"checkout_url": session.get("url"), "session_id": session.get("id")}
