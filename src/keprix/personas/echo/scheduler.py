"""Calendar integration and appointment booking for ECHO."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from keprix.personas.echo.persona import ECHO_PERSONA
from keprix.workspace.repository import workspace_repo

DEFAULT_SLOT_MINUTES = 30
BUSINESS_DAY_START_HOUR = 9
BUSINESS_DAY_END_HOUR = 17


@dataclass(slots=True)
class TimeSlot:
    start_at: datetime
    end_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {"start_at": self.start_at.isoformat(), "end_at": self.end_at.isoformat()}


@dataclass
class BookingResult:
    booked: bool
    event_id: str | None = None
    title: str = ""
    start_at: datetime | None = None
    end_at: datetime | None = None
    confirmation: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "booked": self.booked,
            "event_id": self.event_id,
            "title": self.title,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "confirmation": dict(self.confirmation),
            "message": self.message,
        }


class EchoScheduler:
    """Uses workspace calendar for availability checks and booking."""

    def __init__(
        self,
        *,
        workspace_id: str = "default",
        user_id: str = "default",
        slot_minutes: int = DEFAULT_SLOT_MINUTES,
    ) -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.slot_minutes = slot_minutes
        self.persona = ECHO_PERSONA
        self._user = {"id": user_id, "username": user_id}

    def _overlaps(self, start: datetime, end: datetime, event: dict[str, Any]) -> bool:
        event_start = event["start_at"]
        event_end = event["end_at"]
        if isinstance(event_start, str):
            event_start = datetime.fromisoformat(event_start)
        if isinstance(event_end, str):
            event_end = datetime.fromisoformat(event_end)
        return start < event_end and end > event_start

    def list_busy_events(self, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
        return workspace_repo.list_events(self._user, start=start, end=end)

    def find_available_slots(
        self,
        *,
        start: datetime | None = None,
        days: int = 5,
        count: int = 4,
    ) -> list[TimeSlot]:
        anchor = start or datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        window_end = anchor + timedelta(days=days)
        busy = self.list_busy_events(start=anchor, end=window_end)
        slots: list[TimeSlot] = []
        cursor = anchor
        duration = timedelta(minutes=self.slot_minutes)

        while cursor < window_end and len(slots) < count:
            if cursor.weekday() < 5 and BUSINESS_DAY_START_HOUR <= cursor.hour < BUSINESS_DAY_END_HOUR:
                slot_end = cursor + duration
                if not any(self._overlaps(cursor, slot_end, event) for event in busy):
                    slots.append(TimeSlot(start_at=cursor, end_at=slot_end))
            cursor += duration
            if cursor.hour >= BUSINESS_DAY_END_HOUR:
                next_day = (cursor + timedelta(days=1)).replace(
                    hour=BUSINESS_DAY_START_HOUR, minute=0, second=0, microsecond=0
                )
                cursor = next_day
        return slots

    def book_appointment(
        self,
        *,
        title: str,
        start_at: datetime,
        caller_name: str,
        caller_phone: str = "",
        caller_email: str = "",
        description: str = "",
    ) -> BookingResult:
        end_at = start_at + timedelta(minutes=self.slot_minutes)
        busy = self.list_busy_events(start=start_at, end=end_at)
        if any(self._overlaps(start_at, end_at, event) for event in busy):
            return BookingResult(
                booked=False,
                message="That time is no longer available. Let me offer another slot.",
            )

        details = [
            f"Caller: {caller_name}",
            f"Phone: {caller_phone}" if caller_phone else "",
            f"Email: {caller_email}" if caller_email else "",
            description,
        ]
        event = workspace_repo.create_event(
            self._user,
            title=title,
            description="\n".join(part for part in details if part).strip(),
            location="",
            start_at=start_at,
            end_at=end_at,
        )
        confirmation = self.build_confirmation(
            caller_name=caller_name,
            caller_phone=caller_phone,
            caller_email=caller_email,
            event=event,
        )
        return BookingResult(
            booked=True,
            event_id=str(event["id"]),
            title=title,
            start_at=start_at,
            end_at=end_at,
            confirmation=confirmation,
            message=f"Your appointment is confirmed for {start_at.strftime('%A %d %B at %H:%M')}.",
        )

    def reschedule_appointment(self, event_id: str, *, new_start: datetime) -> BookingResult:
        try:
            existing = workspace_repo.get_event(self._user, event_id)
        except Exception:
            return BookingResult(booked=False, message="I could not find that booking.")
        end_at = new_start + timedelta(minutes=self.slot_minutes)
        busy = [
            event
            for event in self.list_busy_events(start=new_start, end=end_at)
            if str(event.get("id")) != event_id
        ]
        if any(self._overlaps(new_start, end_at, event) for event in busy):
            return BookingResult(booked=False, message="That new time is not available.")
        updated = workspace_repo.update_event(self._user, event_id, start_at=new_start, end_at=end_at)
        return BookingResult(
            booked=True,
            event_id=event_id,
            title=str(updated.get("title") or existing.get("title") or ""),
            start_at=new_start,
            end_at=end_at,
            message=f"Rescheduled to {new_start.strftime('%A %d %B at %H:%M')}.",
        )

    def cancel_appointment(self, event_id: str) -> BookingResult:
        try:
            existing = workspace_repo.get_event(self._user, event_id)
        except Exception:
            return BookingResult(booked=False, message="I could not find that booking.")
        workspace_repo.delete_event(self._user, event_id)
        return BookingResult(
            booked=False,
            event_id=event_id,
            title=str(existing.get("title") or ""),
            message="Your appointment has been cancelled.",
        )

    def build_confirmation(
        self,
        *,
        caller_name: str,
        caller_phone: str,
        caller_email: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        start_at = event["start_at"]
        if isinstance(start_at, str):
            start_at = datetime.fromisoformat(start_at)
        body = (
            f"Hi {caller_name}, your appointment with us is confirmed for "
            f"{start_at.strftime('%A %d %B at %H:%M')}."
        )
        channels: dict[str, Any] = {}
        if caller_email:
            channels["email"] = {
                "to": caller_email,
                "subject": "Appointment confirmation",
                "body": body,
                "status": "queued",
            }
        if caller_phone:
            channels["sms"] = {
                "to": caller_phone,
                "body": body,
                "status": "queued",
            }
        return {
            "confirmation_id": str(uuid4()),
            "channels": channels,
            "message": body,
        }
