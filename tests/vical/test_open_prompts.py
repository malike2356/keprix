"""ICS, webhooks, reminders, intake, deposits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.vical.deposits import create_checkout_session, mark_deposit_paid
from keprix.vical.ics import ics_is_parseable, render_booking_ics
from keprix.vical.intake import IntakeDisqualified, validate_intake_answers
from keprix.vical.notifications import clear_outbox, list_outbox
from keprix.vical.reminders import META_24H, process_reminders
from keprix.vical.routes import router as vical_router
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import vical_store
from keprix.vical.webhooks import sign_payload, verify_signature
from keprix.workspace.repository import workspace_repo


@pytest.fixture(autouse=True)
def clean() -> None:
    workspace_repo.calendar_events.clear()
    vical_store.clear()
    clear_outbox()
    yield
    workspace_repo.calendar_events.clear()
    vical_store.clear()
    clear_outbox()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(vical_router)

    async def fake_user():
        return {"id": "host-1", "username": "host-1"}

    from keprix.auth import dependencies as deps

    app.dependency_overrides[deps.get_current_user] = fake_user
    return TestClient(app)


def _weekday_slot(days: int = 2, hour: int = 10) -> datetime:
    start = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    return start


def test_webhook_signature_roundtrip() -> None:
    body = b'{"event":"vical.booking.confirmed"}'
    secret = "fixture-secret-not-real"
    sig = sign_payload(secret, body)
    assert verify_signature(secret, body, sig)
    assert not verify_signature(secret, body, "sha256=deadbeef")


def test_intake_disqualify() -> None:
    pool = {
        "questions": [
            {
                "id": "ready",
                "type": "single_select",
                "required": True,
                "options": ["yes", "no"],
                "disqualify_answers": ["no"],
                "disqualify_message": "Not ready",
            }
        ]
    }
    with pytest.raises(IntakeDisqualified):
        validate_intake_answers(pool, {"ready": "no"})
    assert validate_intake_answers(pool, {"ready": "yes"})["ready"] == "yes"


def test_public_book_and_ics(client: TestClient) -> None:
    ensure_default_consultation("host-1")
    host = client.get("/api/vical/public/hosts/host-1")
    assert host.status_code == 200, host.text
    start = _weekday_slot()
    booked = client.post(
        "/api/vical/public/hosts/host-1/bookings",
        json={
            "guest_name": "Guest",
            "guest_email": "g@example.com",
            "starts_at": start.isoformat(),
            "event_type_slug": "consultation",
        },
    )
    assert booked.status_code == 201, booked.text
    payload = booked.json()
    assert payload["status"] == "confirmed"
    token = payload["guest_token"]
    ics = client.get("/api/vical/public/bookings/by-token/ics", params={"guest_token": token})
    assert ics.status_code == 200
    assert ics_is_parseable(ics.text)
    assert "BEGIN:VEVENT" in ics.text


def test_reminders_idempotent() -> None:
    ensure_default_consultation("host-1")
    from keprix.vical.bookings import BookingLifecycle

    start = datetime.now(timezone.utc) + timedelta(hours=23, minutes=30)
    # Force inside 24h window regardless of weekend
    booking = BookingLifecycle().create(
        "host-1",
        slug="consultation",
        guest_name="R",
        guest_email="r@example.com",
        starts_at=start,
        skip_slot_check=True,
        source="api",
    )
    assert booking.status == "confirmed"
    first = process_reminders(now=datetime.now(timezone.utc))
    second = process_reminders(now=datetime.now(timezone.utc))
    assert any(item["booking_id"] == booking.id and item["window"] == "24h" for item in first["sent"])
    assert second["sent"] == []
    refreshed = vical_store.get_booking("host-1", booking.id)
    assert META_24H in (refreshed.metadata or {})
    assert any(m.kind == "reminder" for m in list_outbox())


def test_deposit_scaffold_mark_paid(client: TestClient) -> None:
    ensure_default_consultation("host-1")
    et = vical_store.get_event_type_by_slug("host-1", "consultation")
    assert et is not None
    vical_store.update_event_type(
        "host-1",
        et.id,
        requires_deposit=True,
        deposit_minor=500,
        deposit_currency="gbp",
        requires_approval=False,
    )
    start = _weekday_slot(3)
    from keprix.vical.bookings import BookingLifecycle

    booking = BookingLifecycle().create(
        "host-1",
        event_type_id=et.id,
        guest_name="Pay",
        guest_email="pay@example.com",
        starts_at=start,
        skip_slot_check=True,
    )
    assert booking.status == "pending_payment"
    checkout = create_checkout_session("host-1", booking.id)
    assert checkout["pricing"] == "price_data"
    assert checkout["stripe_live"] is False
    paid = mark_deposit_paid(session_id=str(checkout["session_id"]))
    assert paid.status == "confirmed"
    assert paid.workspace_event_id


def test_ics_render_unit() -> None:
    ensure_default_consultation("host-1")
    from keprix.vical.bookings import BookingLifecycle

    booking = BookingLifecycle().create(
        "host-1",
        slug="consultation",
        guest_name="Ics",
        guest_email="i@example.com",
        starts_at=_weekday_slot(),
        skip_slot_check=True,
    )
    body = render_booking_ics(booking, title="Consultation: Ics")
    assert ics_is_parseable(body)
