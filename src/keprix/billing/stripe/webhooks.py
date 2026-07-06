"""Stripe webhook entrypoint (signature verify + dispatch)."""

from __future__ import annotations

import json
from typing import Any

from keprix.billing.webhooks.dispatcher import dispatch_webhook_event, verify_stripe_signature


async def process_stripe_webhook(payload: bytes, signature_header: str | None) -> dict[str, Any]:
    if not verify_stripe_signature(payload, signature_header):
        raise PermissionError("Invalid webhook signature")
    event = json.loads(payload.decode("utf-8"))
    return await dispatch_webhook_event(event)
