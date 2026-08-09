"""Map provider attendee responses to delivery evidence (Prompt 633)."""

from __future__ import annotations

from keprix.vical.calendar.types import AttendeeResponse, DeliveryState


def map_google_response(status: str | None) -> tuple[AttendeeResponse, DeliveryState]:
    raw = (status or "").strip()
    mapping = {
        "accepted": ("accepted", "accepted"),
        "declined": ("declined", "declined"),
        "tentative": ("tentative", "tentative"),
        "needsAction": ("needsAction", "sent"),
        "needs_action": ("needsAction", "sent"),
    }
    return mapping.get(raw, ("unknown", "unknown"))  # type: ignore[return-value]


def map_microsoft_response(status: str | None) -> tuple[AttendeeResponse, DeliveryState]:
    raw = (status or "").strip().lower()
    mapping = {
        "accepted": ("accepted", "accepted"),
        "declined": ("declined", "declined"),
        "tentativelyaccepted": ("tentative", "tentative"),
        "tentative": ("tentative", "tentative"),
        "none": ("needsAction", "sent"),
        "notresponded": ("needsAction", "sent"),
    }
    return mapping.get(raw, ("unknown", "unknown"))  # type: ignore[return-value]


def booking_invitation_view(projection: dict | None) -> dict:
    """Operator-facing invitation evidence (host vs guest separately)."""
    if not projection:
        return {
            "hostEventCreated": False,
            "invitationSendRequested": False,
            "invitationDeliveryState": "unknown",
            "guestResponse": "unknown",
            "provider": "none",
        }
    attendees = projection.get("attendees") or []
    guest = None
    for a in attendees:
        if a.get("email"):
            guest = a
            break
    return {
        "hostEventCreated": bool(projection.get("hostEventCreated")),
        "invitationSendRequested": bool(projection.get("invitationSendRequested")),
        "invitationDeliveryState": projection.get("invitationDeliveryState") or "unknown",
        "guestResponse": (guest or {}).get("responseStatus") or "unknown",
        "provider": projection.get("provider") or "none",
        "providerEventId": projection.get("providerEventId"),
        "icsFallback": projection.get("provider") == "ics",
    }
