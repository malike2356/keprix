"""Outbound lifecycle webhooks for viCal."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any

from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import VcalBooking

logger = logging.getLogger(__name__)


def sign_payload(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    expected = sign_payload(secret, body)
    return hmac.compare_digest(expected, (signature_header or "").strip())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_event_envelope(event: str, booking: VcalBooking) -> dict[str, Any]:
    return {
        "event": event,
        "sent_at": _now_iso(),
        "payload": {
            "booking_id": booking.id,
            "user_id": booking.user_id,
            "host_user_id": booking.host_user_id,
            "status": booking.status,
            "guest_email": booking.guest_email,
            "starts_at": booking.starts_at.isoformat(),
            "ends_at": booking.ends_at.isoformat(),
            "source": booking.source,
        },
    }


def dispatch_booking_webhook(
    booking: VcalBooking,
    event: str,
    *,
    store: VicalStore | None = None,
    transport: Any | None = None,
) -> dict[str, Any]:
    """POST signed JSON to host webhook_url when configured."""
    store = store or vical_store
    if os.environ.get("KEPRIX_VICAL_WEBHOOKS", "1").strip().lower() in {"0", "false", "no", "off"}:
        return {"sent": False, "reason": "disabled"}

    profile = store.get_host_profile(booking.user_id) or {}
    url = (profile.get("webhook_url") or "").strip()
    if not url:
        return {"sent": False, "reason": "no_webhook_url"}

    secret = str(profile.get("webhook_secret") or os.environ.get("KEPRIX_VICAL_WEBHOOK_SECRET") or "dev-vical-webhook")
    envelope = build_event_envelope(event, booking)
    body = json.dumps(envelope, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = sign_payload(secret, body)
    headers = {
        "Content-Type": "application/json",
        "X-Keprix-Signature": signature,
        "X-Keprix-Event": event,
    }

    if transport is not None:
        transport(url, body, headers)
        return {"sent": True, "url": url, "event": event}

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310 - operator-configured URL
            return {"sent": True, "url": url, "event": event, "status": getattr(resp, "status", None)}
    except Exception as exc:
        logger.warning("viCal webhook failed for %s: %s", booking.id, exc)
        return {"sent": False, "reason": str(exc), "event": event}
