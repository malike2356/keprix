"""Provider-neutral calendar adapter types (Prompt 633)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

CalendarProviderId = Literal["google", "microsoft", "ics", "caldav", "none"]
AttendeeResponse = Literal["accepted", "declined", "tentative", "unknown", "needsAction"]
DeliveryState = Literal[
    "pending",
    "sent",
    "delivered",
    "accepted",
    "declined",
    "tentative",
    "failed",
    "unknown",
]
CalendarSendUpdates = Literal["all", "externalOnly", "none"]


@dataclass
class CalendarEventInput:
    workspace_id: str
    user_id: str
    booking_id: str
    summary: str
    starts_at: str
    ends_at: str
    idempotency_key: str
    description: str | None = None
    timezone: str = "UTC"
    location: str | None = None
    guest_email: str | None = None
    guest_name: str | None = None
    join_url: str | None = None
    send_updates: CalendarSendUpdates = "all"
    provider_event_id: str | None = None


@dataclass
class CalendarAttendeeSnapshot:
    email: str
    response_status: AttendeeResponse = "unknown"
    delivery_state: DeliveryState = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "responseStatus": self.response_status,
            "deliveryState": self.delivery_state,
        }


@dataclass
class CalendarAdapterResult:
    ok: bool
    status: str
    provider: CalendarProviderId
    provider_event_id: str | None = None
    etag: str | None = None
    html_link: str | None = None
    organizer_email: str | None = None
    attendees: list[CalendarAttendeeSnapshot] = field(default_factory=list)
    # Host event creation evidence (separate from guest invite)
    host_event_created: bool = False
    # Guest invitation send requested / evidenced separately
    invitation_send_requested: bool = False
    invitation_delivery_state: DeliveryState = "unknown"
    join_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_after_ms: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "provider": self.provider,
            "providerEventId": self.provider_event_id,
            "etag": self.etag,
            "htmlLink": self.html_link,
            "organizerEmail": self.organizer_email,
            "attendees": [a.to_dict() for a in self.attendees],
            "hostEventCreated": self.host_event_created,
            "invitationSendRequested": self.invitation_send_requested,
            "invitationDeliveryState": self.invitation_delivery_state,
            "joinUrl": self.join_url,
            "errorCode": self.error_code,
            "errorMessage": self.error_message,
        }


class CalendarAdapter(Protocol):
    provider: CalendarProviderId

    def create_event(self, input: CalendarEventInput) -> CalendarAdapterResult: ...

    def update_event(self, input: CalendarEventInput) -> CalendarAdapterResult: ...

    def delete_event(
        self,
        *,
        workspace_id: str,
        user_id: str,
        booking_id: str,
        provider_event_id: str,
        idempotency_key: str,
        send_updates: CalendarSendUpdates = "all",
    ) -> CalendarAdapterResult: ...

    def get_event(
        self, *, workspace_id: str, user_id: str, provider_event_id: str
    ) -> CalendarAdapterResult: ...
