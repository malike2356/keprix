"""Guest/host notification hooks for viCal (email templates + optional SMS gate)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from keprix.vical.types import VcalBooking

logger = logging.getLogger(__name__)

NotificationKind = str  # received | confirmed | cancelled | rescheduled | reminder


@dataclass
class NotificationMessage:
    kind: NotificationKind
    to_email: str
    subject: str
    body: str
    booking_id: str
    created_at: str


_OUTBOX: list[NotificationMessage] = []


def clear_outbox() -> None:
    _OUTBOX.clear()


def list_outbox() -> list[NotificationMessage]:
    return list(_OUTBOX)


def _sms_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_SMS_ON_CONFIRM", "0").strip().lower() in {"1", "true", "yes", "on"}


def render_notification(kind: NotificationKind, booking: VcalBooking, *, window: str | None = None) -> NotificationMessage:
    when = booking.starts_at.isoformat()
    subjects = {
        "received": f"Request received: booking {booking.id}",
        "confirmed": f"Confirmed: booking {booking.id}",
        "cancelled": f"Cancelled: booking {booking.id}",
        "rescheduled": f"Rescheduled: booking {booking.id}",
        "reminder": f"Reminder ({window or 'upcoming'}): booking {booking.id}",
    }
    bodies = {
        "received": f"We received your booking request for {when}. Status: {booking.status}.",
        "confirmed": f"Your appointment is confirmed for {when}. Guest token: {booking.guest_token}",
        "cancelled": f"Your appointment for {when} was cancelled.",
        "rescheduled": f"Your appointment was moved to {when}.",
        "reminder": f"Reminder: your appointment starts at {when}.",
    }
    return NotificationMessage(
        kind=kind,
        to_email=booking.guest_email,
        subject=subjects.get(kind, f"viCal: {kind}"),
        body=bodies.get(kind, f"viCal {kind} for {when}"),
        booking_id=booking.id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def notify_booking(
    kind: NotificationKind,
    booking: VcalBooking,
    *,
    window: str | None = None,
    deliver: Callable[[NotificationMessage], None] | None = None,
) -> NotificationMessage:
    message = render_notification(kind, booking, window=window)
    _OUTBOX.append(message)
    if deliver is not None:
        deliver(message)
    else:
        logger.info("viCal notify %s -> %s (%s)", kind, message.to_email, booking.id)

    if kind == "confirmed" and _sms_enabled():
        logger.info("viCal SMS confirm gated on for booking %s (Twilio path not forced)", booking.id)

    return message


def kind_for_status(status: str, *, is_reschedule: bool = False) -> NotificationKind | None:
    if is_reschedule:
        return "rescheduled"
    mapping = {
        "pending_payment": "received",
        "pending_review": "received",
        "confirmed": "confirmed",
        "cancelled": "cancelled",
        "rejected": "cancelled",
    }
    return mapping.get(status)


def notify_dict(message: NotificationMessage) -> dict[str, Any]:
    return {
        "kind": message.kind,
        "to_email": message.to_email,
        "subject": message.subject,
        "body": message.body,
        "booking_id": message.booking_id,
        "created_at": message.created_at,
    }
