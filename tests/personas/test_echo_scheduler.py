"""Tests for ECHO scheduler module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from keprix.personas.echo.scheduler import EchoScheduler
from keprix.workspace.repository import workspace_repo

UTC = timezone.utc


@pytest.fixture
def scheduler() -> EchoScheduler:
    return EchoScheduler(workspace_id="ws-echo", user_id="user-echo")


@pytest.fixture(autouse=True)
def clear_calendar() -> None:
    workspace_repo.calendar_events.clear()
    try:
        from keprix.vical.store import vical_store

        vical_store.clear()
    except Exception:
        pass
    yield
    workspace_repo.calendar_events.clear()
    try:
        from keprix.vical.store import vical_store

        vical_store.clear()
    except Exception:
        pass


def test_find_available_slots_skips_busy_events(scheduler: EchoScheduler) -> None:
    start = datetime.now(UTC).replace(hour=10, minute=0, second=0, microsecond=0)
    workspace_repo.create_event(
        {"id": "user-echo", "username": "user-echo"},
        title="Busy",
        start_at=start,
        end_at=start + timedelta(minutes=30),
    )
    slots = scheduler.find_available_slots(start=start, days=1, count=3)
    assert all(slot.start_at != start for slot in slots)


def test_book_appointment_creates_event(scheduler: EchoScheduler) -> None:
    start = datetime.now(UTC).replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    result = scheduler.book_appointment(
        title="Discovery call",
        start_at=start,
        caller_name="Alex",
        caller_phone="+441234567890",
        caller_email="alex@example.com",
    )
    assert result.booked is True
    assert result.event_id
    assert result.confirmation["channels"]["email"]["to"] == "alex@example.com"
    assert result.confirmation["channels"]["sms"]["to"] == "+441234567890"


def test_book_appointment_rejects_conflict(scheduler: EchoScheduler) -> None:
    start = datetime.now(UTC).replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    first = scheduler.book_appointment(title="First", start_at=start, caller_name="One")
    second = scheduler.book_appointment(title="Second", start_at=start, caller_name="Two")
    assert first.booked is True
    assert second.booked is False


def test_cancel_appointment(scheduler: EchoScheduler) -> None:
    start = datetime.now(UTC).replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=2)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    booked = scheduler.book_appointment(title="Cancel me", start_at=start, caller_name="Sam")
    assert booked.event_id
    cancelled = scheduler.cancel_appointment(str(booked.event_id))
    assert "cancelled" in cancelled.message.lower()
