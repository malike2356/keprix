"""Stripe Checkout session helpers."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.stripe.client import get_stripe_client
from keprix.billing.stripe.products import resolve_price_id

DONATION_MIN_GBP = Decimal("1.00")
DONATION_MAX_GBP = Decimal("500.00")


def donation_amount_to_pence(amount_gbp: float | int | str | Decimal) -> int:
    """Convert GBP to integer pence. Min £1, max £500. Raises ValueError if invalid."""
    try:
        amount = Decimal(str(amount_gbp)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("amount_gbp must be a number") from exc
    if amount < DONATION_MIN_GBP:
        raise ValueError(f"Minimum donation is £{DONATION_MIN_GBP}")
    if amount > DONATION_MAX_GBP:
        raise ValueError(f"Maximum donation is £{DONATION_MAX_GBP}")
    return int(amount * 100)


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
        mode="subscription",
    )
    return {"checkout_url": session.get("url"), "session_id": session.get("id")}


async def create_donation_checkout(
    *,
    donation_id: str = "coffee",
    amount_gbp: float | int | str | Decimal | None = None,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> dict[str, Any]:
    """One-time payment checkout for optional community donations.

    Open amounts use Stripe Checkout ``price_data`` (no new catalog prices).
    Default amount is £1 when omitted.
    """
    cfg = load_billing_config()
    donation = cfg.donation_by_id(donation_id) if cfg else None
    name = donation.name if donation else "Buy me a coffee"
    description = (
        donation.description
        if donation
        else "Optional community support. From £1. Not compulsory."
    )
    currency = (donation.currency if donation else "gbp").lower()
    if currency != "gbp":
        raise ValueError("Open-amount coffee donations are GBP only")

    pence = donation_amount_to_pence(amount_gbp if amount_gbp is not None else DONATION_MIN_GBP)
    product_id = cfg.product.id if cfg else "keprix"
    base_url = os.environ.get("KEPRIX_INSTANCE_URL", "http://localhost:3000").rstrip("/")

    session = await get_stripe_client().create_checkout_session(
        customer_id=None,
        price_data={
            "currency": currency,
            "unit_amount": pence,
            "product_name": name,
            "product_description": description,
        },
        success_url=success_url or f"{base_url}/?donation=thanks",
        cancel_url=cancel_url or f"{base_url}/?donation=cancel",
        trial_days=0,
        metadata={
            "product_id": product_id,
            "donation_id": donation_id,
            "kind": "donation",
            "amount_pence": str(pence),
        },
        mode="payment",
    )
    return {
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
        "donation": {
            "id": donation_id,
            "name": name,
            "description": description,
            "amount": pence,
            "amount_gbp": float(Decimal(pence) / 100),
            "currency": currency,
            "pricing": "price_data",
            "stripe_price_id": donation.stripe_price_id if donation else None,
        },
    }
