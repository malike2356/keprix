"""Dispatch Stripe webhook events with idempotency."""

from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import os
from typing import Any

from keprix.billing.config_loader import load_billing_config
from keprix.billing.store import get_billing_store
from keprix.billing.webhooks.handlers import HANDLERS


def _idempotency_key(event: dict[str, Any]) -> str:
    event_type = str(event.get("type") or "unknown")
    obj = event.get("data", {}).get("object", {})
    obj_id = str(obj.get("id") or event.get("id") or "")
    if event_type == "checkout.session.completed":
        return f"checkout_{obj_id}"
    if event_type.startswith("customer.subscription."):
        suffix = event_type.split(".")[-1]
        return f"sub_{suffix}_{obj_id}"
    if event_type.startswith("invoice."):
        return f"invoice_{obj_id}"
    if event_type == "customer.subscription.trial_will_end":
        return f"trial_end_{obj_id}"
    if event_type.startswith("payment_method."):
        return f"pm_{obj_id}"
    if event_type.startswith("charge."):
        return f"charge_{obj_id}"
    return hashlib.sha256(json.dumps(event, sort_keys=True).encode("utf-8")).hexdigest()


def verify_stripe_signature(payload: bytes, signature_header: str | None) -> bool:
    cfg = load_billing_config()
    secret_env = cfg.webhooks.signing_secret_env if cfg else "STRIPE_WEBHOOK_SECRET"
    secret = os.environ.get(secret_env, "").strip()
    if not secret:
        return os.environ.get("KEPRIX_BILLING_ALLOW_UNSIGNED_WEBHOOKS", "").lower() in {"1", "true", "yes"}
    if not signature_header:
        return False
    parts = dict(item.split("=", 1) for item in signature_header.split(",") if "=" in item)
    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False
    signed = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def dispatch_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    store = get_billing_store()
    key = _idempotency_key(event)
    if await store.webhook_seen(key):
        return {"ok": True, "duplicate": True, "idempotency_key": key}

    event_type = str(event.get("type") or "")
    handler = HANDLERS.get(event_type)
    if handler is None:
        result = {"ok": True, "ignored": True, "type": event_type}
    else:
        result = handler(event)
        if inspect.isawaitable(result):
            result = await result

    await store.mark_webhook(key, {"type": event_type, "result": result})
    return {"idempotency_key": key, **result}
