"""Zoom webhook signature validation and dedupe (Prompt 632)."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

from keprix.vical.saga.ledger import get_saga_ledger


def zoom_webhook_secret() -> str:
    return (
        (os.environ.get("KEPRIX_CONCIERGE_ZOOM_WEBHOOK_SECRET") or "").strip()
        or (os.environ.get("ZOOM_WEBHOOK_SECRET") or "").strip()
    )


def verify_zoom_webhook_signature(
    *,
    body: bytes | str,
    timestamp: str | None,
    signature: str | None,
    secret: str | None = None,
    max_skew_seconds: int = 300,
) -> bool:
    secret = (secret if secret is not None else zoom_webhook_secret()).strip()
    if not secret or not signature or not timestamp:
        return False
    try:
        ts = int(timestamp)
    except Exception:
        return False
    if abs(int(time.time()) - ts) > max_skew_seconds:
        return False
    raw = body.encode("utf-8") if isinstance(body, str) else body
    message = f"v0:{timestamp}:".encode("utf-8") + raw
    digest = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature.strip())


def handle_zoom_webhook(
    *,
    payload: dict[str, Any],
    body: bytes | str,
    timestamp: str | None,
    signature: str | None,
    secret: str | None = None,
) -> dict[str, Any]:
    # Zoom URL validation challenge
    if payload.get("event") == "endpoint.url_validation":
        plain = str((payload.get("payload") or {}).get("plainToken") or "")
        sec = (secret if secret is not None else zoom_webhook_secret()).strip()
        hashed = hmac.new(sec.encode("utf-8"), plain.encode("utf-8"), hashlib.sha256).hexdigest()
        return {
            "ok": True,
            "challenge": True,
            "plainToken": plain,
            "encryptedToken": hashed,
        }

    if not verify_zoom_webhook_signature(
        body=body, timestamp=timestamp, signature=signature, secret=secret
    ):
        return {"ok": False, "error_code": "webhook_forgery"}

    event_type = str(payload.get("event") or "")
    event_ts = str(payload.get("event_ts") or timestamp or "")
    obj = (payload.get("payload") or {}).get("object") or {}
    meeting_id = str(obj.get("id") or obj.get("uuid") or "")
    event_id = f"{event_type}:{meeting_id}:{event_ts}" or hashlib.sha256(
        (body if isinstance(body, bytes) else body.encode("utf-8"))
    ).hexdigest()

    receipt = get_saga_ledger().record_webhook_receipt(
        provider="zoom",
        event_id=event_id,
        event_type=event_type,
        payload=payload,
    )
    return {
        "ok": True,
        "duplicate": receipt.get("duplicate", False),
        "eventId": event_id,
        "eventType": event_type,
        "meetingId": meeting_id or None,
        "reconciled": True,
    }


__all__ = ["handle_zoom_webhook", "verify_zoom_webhook_signature", "zoom_webhook_secret"]
