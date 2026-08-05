"""viCal domain types for Keprix."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Literal

BookingStatus = Literal[
    "pending_payment",
    "pending_review",
    "confirmed",
    "cancelled",
    "rejected",
]

ACTIVE_BOOKING_STATUSES: frozenset[str] = frozenset(
    {"pending_payment", "pending_review", "confirmed"},
)

BookingSource = Literal["public", "api", "agent", "echo", "voice"]

LocationMode = Literal["unspecified", "in_person", "phone", "video", "custom"]

SessionOutcome = Literal["attended", "no_show"]


def _dt_iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


@dataclass
class VcalEventType:
    id: str
    user_id: str
    host_user_id: str
    slug: str
    name: str
    duration_minutes: int = 30
    buffer_before_minutes: int = 0
    buffer_after_minutes: int = 0
    min_notice_minutes: int = 120
    horizon_days: int = 30
    location_mode: LocationMode = "unspecified"
    requires_approval: bool = False
    requires_deposit: bool = False
    deposit_minor: int | None = None
    deposit_currency: str | None = None
    intake_pool_id: str | None = None
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    workspace_id: str | None = None
    tenant_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = _dt_iso(self.created_at)
        payload["updated_at"] = _dt_iso(self.updated_at)
        return payload


@dataclass
class VcalAvailabilityRule:
    id: str
    user_id: str
    host_user_id: str
    day_of_week: int  # 0=Monday .. 6=Sunday (Python weekday)
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    timezone: str = "UTC"
    event_type_id: str | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["created_at"] = _dt_iso(self.created_at)
        payload["updated_at"] = _dt_iso(self.updated_at)
        return payload


@dataclass
class VcalBlackoutDate:
    id: str
    user_id: str
    starts_on: date
    ends_on: date
    host_user_id: str | None = None
    reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    workspace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["starts_on"] = _dt_iso(self.starts_on)
        payload["ends_on"] = _dt_iso(self.ends_on)
        payload["created_at"] = _dt_iso(self.created_at)
        payload["updated_at"] = _dt_iso(self.updated_at)
        return payload


@dataclass
class VcalBooking:
    id: str
    user_id: str
    event_type_id: str
    host_user_id: str
    guest_name: str
    guest_email: str
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    guest_token: str
    source: BookingSource = "api"
    meeting_url: str | None = None
    workspace_event_id: str | None = None
    intake_answers: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None
    session_outcome: SessionOutcome | None = None
    cancel_reschedule: dict[str, Any] = field(default_factory=dict)
    contact_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    workspace_id: str | None = None
    tenant_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["starts_at"] = _dt_iso(self.starts_at)
        payload["ends_at"] = _dt_iso(self.ends_at)
        payload["created_at"] = _dt_iso(self.created_at)
        payload["updated_at"] = _dt_iso(self.updated_at)
        return payload


@dataclass
class VcalSlotLock:
    id: str
    user_id: str
    host_user_id: str
    starts_at: datetime
    ends_at: datetime
    holder_token: str
    expires_at: datetime
    event_type_id: str | None = None
    workspace_id: str | None = None
    created_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["starts_at"] = _dt_iso(self.starts_at)
        payload["ends_at"] = _dt_iso(self.ends_at)
        payload["expires_at"] = _dt_iso(self.expires_at)
        payload["created_at"] = _dt_iso(self.created_at)
        return payload
