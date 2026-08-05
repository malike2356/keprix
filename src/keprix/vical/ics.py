"""ICS generation for viCal bookings."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.vical.types import VcalBooking


def _fmt_dt(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def booking_uid(booking: VcalBooking) -> str:
    return f"vical-{booking.id}@keprix"


def render_booking_ics(
    booking: VcalBooking,
    *,
    title: str,
    description: str | None = None,
    location: str | None = None,
) -> str:
    """Return a single VEVENT calendar document for a booking."""
    desc = description or f"viCal booking with {booking.guest_name} ({booking.guest_email})"
    loc = location or booking.meeting_url or ""
    stamp = _fmt_dt(booking.updated_at or booking.created_at or datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Keprix//viCal//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{booking_uid(booking)}",
        f"DTSTAMP:{stamp}",
        f"DTSTART:{_fmt_dt(booking.starts_at)}",
        f"DTEND:{_fmt_dt(booking.ends_at)}",
        f"SUMMARY:{_escape(title)}",
        f"DESCRIPTION:{_escape(desc)}",
        f"LOCATION:{_escape(loc)}",
        f"STATUS:{'CANCELLED' if booking.status in {'cancelled', 'rejected'} else 'CONFIRMED'}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines)


def ics_is_parseable(payload: str) -> bool:
    return "BEGIN:VCALENDAR" in payload and "BEGIN:VEVENT" in payload and "UID:" in payload


def booking_ics_dict(booking: VcalBooking, *, title: str) -> dict[str, Any]:
    body = render_booking_ics(booking, title=title)
    return {
        "uid": booking_uid(booking),
        "filename": f"vical-{booking.id}.ics",
        "content_type": "text/calendar; charset=utf-8",
        "body": body,
    }
