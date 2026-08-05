"""Idempotent reminder runner for confirmed viCal bookings."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.vical.notifications import notify_booking
from keprix.vical.store import VicalStore, vical_store
from keprix.vical.webhooks import dispatch_booking_webhook

logger = logging.getLogger(__name__)

META_24H = "reminder_24h_sent_at"
META_1H = "reminder_1h_sent_at"


def _channel_reminders_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_CHANNEL_REMINDERS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _try_channel_reminder(booking, *, window: str) -> dict[str, Any]:
    """Best-effort Telegram/home deliver via send_message when enabled."""
    if not _channel_reminders_enabled():
        return {"sent": False, "reason": "disabled"}
    message = (
        f"viCal reminder ({window}): {booking.guest_name} at {booking.starts_at.isoformat()} "
        f"(booking {booking.id})"
    )
    try:
        target = os.environ.get("KEPRIX_VICAL_REMINDER_TARGET") or ""
        if not target:
            return {"sent": False, "reason": "no_target"}
        from tools.send_message_tool import send_message_tool

        result = send_message_tool(
            {
                "action": "send",
                "target": target,
                "message": message,
            }
        )
        return {"sent": True, "result": str(result)[:200]}
    except Exception as exc:
        logger.info("viCal channel reminder skipped: %s", exc)
        return {"sent": False, "reason": str(exc)}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def reminder_windows() -> dict[str, timedelta]:
    """Windows prior to start_at. Override with minutes via env."""
    try:
        h24 = int(os.environ.get("KEPRIX_VICAL_REMINDER_24H_MIN", str(24 * 60)))
    except ValueError:
        h24 = 24 * 60
    try:
        h1 = int(os.environ.get("KEPRIX_VICAL_REMINDER_1H_MIN", "60"))
    except ValueError:
        h1 = 60
    return {
        "24h": timedelta(minutes=max(1, h24)),
        "1h": timedelta(minutes=max(1, h1)),
    }


def reminders_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_REMINDERS", "1").strip().lower() not in {"0", "false", "no", "off"}


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _due(booking_start: datetime, window: timedelta, now: datetime) -> bool:
    start = _aware(booking_start)
    target = start - window
    # Send within a generous tick so scheduler cadence does not miss the window.
    skew = timedelta(minutes=30)
    return target - skew <= now <= start


def process_reminders(
    *,
    store: VicalStore | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Send 24h and 1h reminders once each for confirmed future bookings."""
    if not reminders_enabled():
        return {"ok": True, "enabled": False, "sent": []}

    store = store or vical_store
    now = now or _now()
    windows = reminder_windows()
    sent: list[dict[str, str]] = []

    for booking in list(store.bookings.values()):
        if booking.status != "confirmed":
            continue
        if _aware(booking.starts_at) <= now:
            continue
        meta = dict(booking.metadata or {})
        changed = False

        if META_24H not in meta and _due(booking.starts_at, windows["24h"], now):
            notify_booking("reminder", booking, window="24h")
            dispatch_booking_webhook(booking, "vical.booking.reminder_24h", store=store)
            _try_channel_reminder(booking, window="24h")
            meta[META_24H] = now.isoformat()
            changed = True
            sent.append({"booking_id": booking.id, "window": "24h"})

        if META_1H not in meta and _due(booking.starts_at, windows["1h"], now):
            notify_booking("reminder", booking, window="1h")
            dispatch_booking_webhook(booking, "vical.booking.reminder_1h", store=store)
            _try_channel_reminder(booking, window="1h")
            meta[META_1H] = now.isoformat()
            changed = True
            sent.append({"booking_id": booking.id, "window": "1h"})

        if changed:
            store.update_booking(booking.user_id, booking.id, metadata=meta)

    return {"ok": True, "enabled": True, "sent": sent, "count": len(sent)}
