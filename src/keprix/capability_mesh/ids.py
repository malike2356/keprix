"""Shared object ID conventions and hop resolvers for the capability mesh."""

from __future__ import annotations

from typing import Any

from keprix.vical.store import IsolationError, VicalStore, vical_store
from keprix.vical.types import VcalBooking

OBJECT_TYPES = (
    "contact",
    "calendar_event",
    "vical_booking",
    "company_number",
    "document",
    "session",
    "memory_item",
    "playbook",
    "cron_job",
    "vault_secret",
)

# Canonical field names used across modules.
ID_FIELDS = {
    "contact": "contact_id",
    "calendar_event": "workspace_event_id",
    "vical_booking": "vical_booking_id",
    "company_number": "company_number",
}


def resolve_booking_links(
    user_id: str,
    booking_id: str,
    *,
    store: VicalStore | None = None,
) -> dict[str, Any]:
    """Return hop targets for a booking (calendar event, contact)."""
    store = store or vical_store
    booking = store.get_booking(user_id, booking_id)
    return {
        "booking_id": booking.id,
        "workspace_event_id": booking.workspace_event_id,
        "contact_id": booking.contact_id,
        "guest_email": booking.guest_email,
        "calendar_path": (
            f"/calendar?event={booking.workspace_event_id}" if booking.workspace_event_id else None
        ),
        "contact_path": f"/contacts?id={booking.contact_id}" if booking.contact_id else None,
        "vical_path": f"/vical?booking={booking.id}",
    }


def find_booking_for_event(
    user_id: str,
    workspace_event_id: str,
    *,
    store: VicalStore | None = None,
) -> VcalBooking | None:
    store = store or vical_store
    for booking in store.list_bookings(user_id):
        if str(booking.workspace_event_id or "") == str(workspace_event_id):
            return booking
    return None


def find_booking_by_metadata_event(
    user_id: str,
    event: dict[str, Any],
    *,
    store: VicalStore | None = None,
) -> VcalBooking | None:
    meta = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    booking_id = meta.get("vical_booking_id") or meta.get("booking_id")
    store = store or vical_store
    if booking_id:
        try:
            return store.get_booking(user_id, str(booking_id))
        except IsolationError:
            return None
    return find_booking_for_event(user_id, str(event.get("id") or ""), store=store)


def calendar_event_metadata_for_booking(booking: VcalBooking) -> dict[str, Any]:
    return {
        "vical_booking_id": booking.id,
        "contact_id": booking.contact_id,
        "guest_email": booking.guest_email,
        "source": "vical",
    }
