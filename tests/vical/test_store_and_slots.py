"""viCal domain store and slot engine tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.vical.busy import BusyReader
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.slots import SlotEngine
from keprix.vical.store import IsolationError, VicalStore
from keprix.workspace.repository import workspace_repo


@pytest.fixture
def store(tmp_path: Path) -> VicalStore:
    path = tmp_path / "vical_store.json"
    repo = VicalStore(path=path)
    yield repo
    repo.clear()


@pytest.fixture(autouse=True)
def clear_calendar() -> None:
    workspace_repo.calendar_events.clear()
    yield
    workspace_repo.calendar_events.clear()


def test_insert_event_type_rule_blackout_booking(store: VicalStore) -> None:
    user = "user-a"
    et = store.create_event_type(user_id=user, slug="consult", name="Consult", duration_minutes=30)
    rule = store.create_availability_rule(
        user_id=user,
        day_of_week=0,
        start_time="09:00",
        end_time="17:00",
    )
    bo = store.create_blackout(
        user_id=user,
        starts_on=date(2026, 8, 10),
        ends_on=date(2026, 8, 10),
        reason="Bank holiday",
    )
    start = datetime(2026, 8, 11, 10, 0, tzinfo=timezone.utc)
    booking = store.create_booking(
        user_id=user,
        event_type_id=et.id,
        guest_name="Alex",
        guest_email="alex@example.com",
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
        source="api",
    )
    assert rule.id in store.availability_rules
    assert bo.reason == "Bank holiday"
    assert booking.guest_token
    assert store.get_booking(user, booking.id).status == "confirmed"


def test_isolation_blocks_other_user(store: VicalStore) -> None:
    et = store.create_event_type(user_id="owner", slug="a", name="A")
    with pytest.raises(IsolationError):
        store.get_event_type("intruder", et.id)


def test_list_bookings_by_host_and_range(store: VicalStore) -> None:
    user = "host-1"
    et = store.create_event_type(user_id=user, slug="call", name="Call")
    t0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
    store.create_booking(
        user_id=user,
        event_type_id=et.id,
        guest_name="A",
        guest_email="a@x.com",
        starts_at=t0,
        ends_at=t0 + timedelta(minutes=30),
    )
    store.create_booking(
        user_id=user,
        event_type_id=et.id,
        guest_name="B",
        guest_email="b@x.com",
        starts_at=t1,
        ends_at=t1 + timedelta(minutes=30),
    )
    store.create_booking(
        user_id=user,
        event_type_id=et.id,
        guest_name="C",
        guest_email="c@x.com",
        starts_at=t2,
        ends_at=t2 + timedelta(minutes=30),
    )
    rows = store.list_bookings(
        user,
        host_user_id=user,
        start=datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 2, 0, 0, tzinfo=timezone.utc),
    )
    assert len(rows) == 2
    assert {r.guest_email for r in rows} == {"a@x.com", "b@x.com"}


def test_seed_consultation_weekdays(store: VicalStore) -> None:
    result = ensure_default_consultation("seed-user", store=store)
    assert result["created_event_type"] is True
    et = result["event_type"]
    assert et.slug == "consultation"
    assert et.duration_minutes == 30
    rules = store.list_availability_rules("seed-user", host_user_id="seed-user")
    assert len(rules) == 5
    assert {r.day_of_week for r in rules} == {0, 1, 2, 3, 4}
    # idempotent
    again = ensure_default_consultation("seed-user", store=store)
    assert again["created_event_type"] is False
    assert again["created_rules"] == 0


def test_slot_engine_skips_workspace_busy(store: VicalStore) -> None:
    user = "slot-user"
    ensure_default_consultation(user, store=store)
    # pick next weekday 10:00 UTC
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    workspace_repo.create_event(
        {"id": user, "username": user},
        title="Busy",
        start_at=start,
        end_at=start + timedelta(minutes=30),
    )
    engine = SlotEngine(store=store, busy_reader=BusyReader(store=store))
    slots = engine.offer_slots(user, slug="consultation", start=start, count=5, now=start - timedelta(hours=2))
    assert all(slot.start_at != start for slot in slots)


def test_slot_lock_contention(store: VicalStore) -> None:
    user = "lock-user"
    ensure_default_consultation(user, store=store)
    start = datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc)  # Monday
    end = start + timedelta(minutes=30)
    engine = SlotEngine(store=store)
    first = engine.acquire_lock(user, host_user_id=user, starts_at=start, ends_at=end)
    assert first.holder_token
    with pytest.raises(ValueError, match="locked"):
        engine.acquire_lock(user, host_user_id=user, starts_at=start, ends_at=end)


def test_blackout_blocks_slots(store: VicalStore) -> None:
    user = "bo-user"
    ensure_default_consultation(user, store=store)
    # next Monday-Friday in horizon
    day = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)  # Monday
    store.create_blackout(user_id=user, starts_on=day.date(), ends_on=day.date(), host_user_id=user)
    engine = SlotEngine(store=store)
    slots = engine.offer_slots(
        user,
        slug="consultation",
        start=day,
        count=10,
        now=day - timedelta(days=1),
    )
    assert all(slot.start_at.date() != day.date() for slot in slots)
