"""Stripe Customer Portal session helpers."""

from __future__ import annotations

import os
from typing import Any

from keprix.billing.store import get_billing_store
from keprix.billing.stripe.client import get_stripe_client


async def create_customer_portal_session(user_id: str, *, return_url: str | None = None) -> dict[str, Any]:
    customer = await get_billing_store().get_customer(user_id)
    if not customer or not customer.get("stripe_customer_id"):
        raise ValueError("No Stripe customer on file")
    base_url = os.environ.get("KEPRIX_INSTANCE_URL", "http://localhost:3000").rstrip("/")
    session = await get_stripe_client().create_portal_session(
        customer_id=str(customer["stripe_customer_id"]),
        return_url=return_url or f"{base_url}/settings/billing",
    )
    return {"portal_url": session.get("url"), "session_id": session.get("id")}
