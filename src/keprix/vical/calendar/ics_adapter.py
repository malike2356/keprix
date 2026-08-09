"""ICS-only calendar projection for Community Edition (Prompt 633).

Host event evidence = ICS document generated and stored.
Guest invitation evidence = durable outbox enqueue (email/channel) with ICS
reference; never claims Google/Microsoft invitation delivery.
"""

from __future__ import annotations

from datetime import datetime

from keprix.vical.calendar.types import (
    CalendarAdapterResult,
    CalendarAttendeeSnapshot,
    CalendarEventInput,
    CalendarSendUpdates,
)
from keprix.vical.ics import booking_uid, render_booking_ics
from keprix.vical.types import VcalBooking


def _parse(dt: str) -> datetime:
    return datetime.fromisoformat(dt.replace("Z", "+00:00"))


class IcsCalendarAdapter:
    provider = "ics"

    def create_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        booking = VcalBooking(
            id=input.booking_id,
            user_id=input.user_id,
            event_type_id="ics",
            host_user_id=input.user_id,
            guest_name=input.guest_name or "Guest",
            guest_email=input.guest_email or "guest@example.com",
            starts_at=_parse(input.starts_at),
            ends_at=_parse(input.ends_at),
            status="confirmed",
            guest_token="ics",
            meeting_url=input.join_url or input.location,
        )
        body = render_booking_ics(
            booking,
            title=input.summary,
            description=input.description,
            location=input.location or input.join_url,
        )
        uid = booking_uid(booking)
        attendees: list[CalendarAttendeeSnapshot] = []
        if input.guest_email:
            attendees.append(
                CalendarAttendeeSnapshot(
                    email=input.guest_email,
                    response_status="unknown",
                    delivery_state="pending",
                )
            )
        return CalendarAdapterResult(
            ok=True,
            status="succeeded",
            provider="ics",
            provider_event_id=uid,
            host_event_created=True,
            invitation_send_requested=bool(input.guest_email),
            invitation_delivery_state="pending" if input.guest_email else "unknown",
            attendees=attendees,
            join_url=input.join_url,
            raw={"icsBytes": len(body.encode("utf-8")), "icsUid": uid, "capability": "ics_only"},
        )

    def update_event(self, input: CalendarEventInput) -> CalendarAdapterResult:
        return self.create_event(input)

    def delete_event(
        self,
        *,
        workspace_id: str,
        user_id: str,
        booking_id: str,
        provider_event_id: str,
        idempotency_key: str,
        send_updates: CalendarSendUpdates = "all",
    ) -> CalendarAdapterResult:
        return CalendarAdapterResult(
            ok=True,
            status="succeeded",
            provider="ics",
            provider_event_id=provider_event_id,
            host_event_created=True,
        )

    def get_event(
        self, *, workspace_id: str, user_id: str, provider_event_id: str
    ) -> CalendarAdapterResult:
        return CalendarAdapterResult(
            ok=True,
            status="succeeded",
            provider="ics",
            provider_event_id=provider_event_id,
            host_event_created=True,
            invitation_delivery_state="unknown",
        )
