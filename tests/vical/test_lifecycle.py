"""Booking lifecycle + calendar bridge tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.vical.bookings import BookingLifecycle, BookingLifecycleError
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore
from keprix.workspace.repository import workspace_repo


@pytest.fixture
def store(tmp_path: Path) -> VicalStore:
    repo = VicalStore(path=tmp_path / "vical.json")
    yield repo
    repo.clear()


@pytest.fixture(autouse=True)
def clear_calendar() -> None:
    workspace_repo.calendar_events.clear()
    yield
    workspace_repo.calendar_events.clear()


def _next_weekday_at(hour: int = 10) -> datetime:
    start = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    return start


def test_confirm_creates_calendar_event(store: VicalStore) -> None:
    user = "life-1"
    ensure_default_consultation(user, store=store)
    life = BookingLifecycle(store=store)
    start = _next_weekday_at(10)
    booking = life.create(
        user,
        slug="consultation",
        guest_name="Alex",
        guest_email="alex@example.com",
        starts_at=start,
        source="api",
    )
    assert booking.status == "confirmed"
    assert booking.workspace_event_id
    assert booking.workspace_event_id in workspace_repo.calendar_events


def test_approval_required_stays_pending(store: VicalStore) -> None:
    user = "life-2"
    et = store.create_event_type(
        user_id=user,
        slug="review",
        name="Review",
        requires_approval=True,
        duration_minutes=30,
        min_notice_minutes=0,
    )
    for day in range(5):
        store.create_availability_rule(
            user_id=user,
            day_of_week=day,
            start_time="09:00",
            end_time="17:00",
        )
    life = BookingLifecycle(store=store)
    start = _next_weekday_at(11)
    booking = life.create(
        user,
        event_type_id=et.id,
        guest_name="Sam",
        guest_email="sam@example.com",
        starts_at=start,
        skip_slot_check=True,
    )
    assert booking.status == "pending_review"
    assert booking.workspace_event_id is None
    approved = life.approve(user, booking.id)
    assert approved.status == "confirmed"
    assert approved.workspace_event_id


def test_cancel_removes_calendar_event(store: VicalStore) -> None:
    user = "life-3"
    ensure_default_consultation(user, store=store)
    life = BookingLifecycle(store=store)
    start = _next_weekday_at(12)
    booking = life.create(
        user,
        slug="consultation",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=start,
        skip_slot_check=True,
    )
    event_id = booking.workspace_event_id
    assert event_id
    cancelled = life.cancel(user, booking.id)
    assert cancelled.status == "cancelled"
    assert event_id not in workspace_repo.calendar_events


def test_reschedule_moves_calendar_event(store: VicalStore) -> None:
    user = "life-4"
    ensure_default_consultation(user, store=store)
    life = BookingLifecycle(store=store)
    start = _next_weekday_at(13)
    booking = life.create(
        user,
        slug="consultation",
        guest_name="Jo",
        guest_email="jo@example.com",
        starts_at=start,
        skip_slot_check=True,
    )
    new_start = start + timedelta(hours=2)
    updated = life.reschedule(user, booking.id, starts_at=new_start)
    assert updated.starts_at == new_start
    assert updated.workspace_event_id
    event = workspace_repo.calendar_events[updated.workspace_event_id]
    assert event["start_at"] == new_start


def test_double_book_rejected(store: VicalStore) -> None:
    user = "life-5"
    ensure_default_consultation(user, store=store)
    life = BookingLifecycle(store=store)
    start = _next_weekday_at(14)
    first = life.create(
        user,
        slug="consultation",
        guest_name="One",
        guest_email="one@example.com",
        starts_at=start,
        skip_slot_check=True,
    )
    assert first.status == "confirmed"
    with pytest.raises(BookingLifecycleError):
        life.create(
            user,
            slug="consultation",
            guest_name="Two",
            guest_email="two@example.com",
            starts_at=start,
        )
