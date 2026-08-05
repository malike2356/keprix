"""Meeting URL / conferencing helpers for viCal confirmations."""

from __future__ import annotations

import logging
import os
from typing import Any

from keprix.vical.store import VicalStore, vical_store
from keprix.vical.types import VcalBooking

logger = logging.getLogger(__name__)


def calendar_sync_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_CALENDAR_SYNC", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def resolve_meeting_url(
    booking: VcalBooking,
    *,
    store: VicalStore | None = None,
    explicit: str | None = None,
) -> str | None:
    """Prefer explicit URL, then host template, then leave empty for CalDAV/workspace path."""
    if explicit and explicit.strip():
        return explicit.strip()
    if booking.meeting_url:
        return booking.meeting_url

    store = store or vical_store
    profile = store.get_host_profile(booking.user_id) or {}
    template = (profile.get("meeting_url_template") or "").strip()
    if template:
        return (
            template.replace("{booking_id}", booking.id)
            .replace("{guest_email}", booking.guest_email)
            .replace("{host_user_id}", booking.host_user_id)
        )

    # Optional GWS Meet hook when already connected; never invent OAuth here.
    if os.environ.get("KEPRIX_VICAL_GWS_MEET", "0").strip().lower() in {"1", "true", "yes", "on"}:
        try:
            # Soft probe only; adapter may be absent in CE.
            from keprix.integrations.google_workspace import tools_calendar  # noqa: F401

            logger.info("GWS Meet flag on; host should set meeting_url_template or explicit URL")
        except Exception:
            pass
    return None


def apply_meeting_url_on_confirm(
    user_id: str,
    booking: VcalBooking,
    *,
    store: VicalStore | None = None,
    explicit: str | None = None,
) -> VcalBooking:
    store = store or vical_store
    url = resolve_meeting_url(booking, store=store, explicit=explicit)
    if not url or booking.meeting_url == url:
        return booking
    return store.update_booking(user_id, booking.id, meeting_url=url)


def sync_notes() -> dict[str, Any]:
    """Runbook snapshot for operators (no secrets)."""
    return {
        "primary": "Workspace calendar bridge + CalDAV push from /calendar sources",
        "flag": "KEPRIX_VICAL_CALENDAR_SYNC",
        "enabled": calendar_sync_enabled(),
        "conferencing_order": [
            "explicit meeting_url on create",
            "host meeting_url_template",
            "optional KEPRIX_VICAL_GWS_MEET documentation path",
        ],
        "docs": "/docs/features/vical.md",
    }
