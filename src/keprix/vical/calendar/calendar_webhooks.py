"""Google Calendar push notification receiver (Prompt 633)."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from keprix.vical.calendar.projection_store import get_projection_store
from keprix.vical.calendar.reconcile import apply_attendee_responses, repair_projection_from_provider
from keprix.vical.saga.ledger import get_saga_ledger


def google_calendar_webhook_token() -> str:
    return (os.environ.get("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN") or "").strip()


def verify_google_calendar_webhook(
    *,
    channel_token: str | None,
    channel_id: str | None,
    expected_token: str | None = None,
) -> bool:
    secret = (expected_token if expected_token is not None else google_calendar_webhook_token()).strip()
    if not secret or not channel_token or not channel_id:
        return False
    return hmac.compare_digest(secret, channel_token.strip())


def handle_google_calendar_webhook(
    *,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
    expected_token: str | None = None,
) -> dict[str, Any]:
    """Validate Google push headers, dedupe, and reconcile when booking mapped.

    Google Calendar push notifications are often empty-body with X-Goog-* headers.
    Full event payload may be absent; then we mark receipt and optionally repair.
    """
    body = body or {}
    channel_id = (
        headers.get("X-Goog-Channel-ID")
        or headers.get("x-goog-channel-id")
        or body.get("channelId")
        or ""
    )
    resource_id = (
        headers.get("X-Goog-Resource-ID")
        or headers.get("x-goog-resource-id")
        or body.get("resourceId")
        or ""
    )
    resource_state = (
        headers.get("X-Goog-Resource-State")
        or headers.get("x-goog-resource-state")
        or body.get("resourceState")
        or "exists"
    )
    channel_token = (
        headers.get("X-Goog-Channel-Token")
        or headers.get("x-goog-channel-token")
        or body.get("channelToken")
    )
    message_number = (
        headers.get("X-Goog-Message-Number")
        or headers.get("x-goog-message-number")
        or "0"
    )

    if not verify_google_calendar_webhook(
        channel_token=channel_token, channel_id=channel_id, expected_token=expected_token
    ):
        return {"ok": False, "error_code": "webhook_forgery"}

    event_id = f"google:{channel_id}:{resource_id}:{resource_state}:{message_number}"
    if not channel_id and not resource_id:
        event_id = "google:" + hashlib.sha256(repr(sorted(headers.items())).encode()).hexdigest()[:32]

    receipt = get_saga_ledger().record_webhook_receipt(
        provider="google_calendar",
        event_id=event_id,
        event_type=str(resource_state),
        payload={"headers": dict(headers), "body": body},
    )
    if receipt.get("duplicate"):
        return {
            "ok": True,
            "duplicate": True,
            "eventId": event_id,
            "reconciled": False,
        }

    workspace_id = str(body.get("workspaceId") or headers.get("X-Keprix-Workspace-Id") or "")
    booking_id = str(body.get("bookingId") or headers.get("X-Keprix-Booking-Id") or "")
    user_id = str(body.get("userId") or headers.get("X-Keprix-User-Id") or "")

    # Optional inline attendee update (tests / enriched relays)
    attendees = body.get("attendees")
    if workspace_id and booking_id and isinstance(attendees, list):
        applied = apply_attendee_responses(
            workspace_id=workspace_id,
            booking_id=booking_id,
            provider="google",
            attendees=attendees,
        )
        return {
            "ok": True,
            "duplicate": False,
            "eventId": event_id,
            "reconciled": True,
            "invitation": applied.get("invitation"),
        }

    if workspace_id and booking_id and user_id and resource_state in {"exists", "update", "sync"}:
        repaired = repair_projection_from_provider(
            workspace_id=workspace_id,
            user_id=user_id,
            booking_id=booking_id,
            provider="google",
        )
        return {
            "ok": True,
            "duplicate": False,
            "eventId": event_id,
            "reconciled": bool(repaired.get("ok")),
            "repair": repaired,
        }

    # Channel sync without booking mapping: durable receipt only
    store = get_projection_store()
    if channel_id and workspace_id:
        store.upsert_watch(
            workspace_id=workspace_id,
            user_id=user_id or "unknown",
            provider="google",
            channel_id=channel_id,
            resource_id=resource_id or None,
            expiration_at=str(body.get("expiration") or "2099-01-01T00:00:00+00:00"),
        )

    return {
        "ok": True,
        "duplicate": False,
        "eventId": event_id,
        "reconciled": False,
        "resourceState": resource_state,
    }


__all__ = [
    "google_calendar_webhook_token",
    "handle_google_calendar_webhook",
    "verify_google_calendar_webhook",
]
