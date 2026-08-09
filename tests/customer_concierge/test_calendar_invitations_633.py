"""Calendar invitations, durable outbox, reconciliation (Prompt 633)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from keprix.vical.calendar.calendar_webhooks import (
    handle_google_calendar_webhook,
    verify_google_calendar_webhook,
)
from keprix.vical.calendar.google_adapter import GoogleCalendarAdapter
from keprix.vical.calendar.projection_store import reset_projection_store_for_tests
from keprix.vical.calendar.reconcile import apply_attendee_responses
from keprix.vical.calendar.sync_booking import (
    CalendarSyncDeps,
    project_booking_calendar,
    renew_expiring_watches,
)
from keprix.vical.ics import render_booking_ics
from keprix.vical.notifications import clear_outbox, list_outbox, notify_booking
from keprix.vical.saga import SagaDeps, book_with_saga
from keprix.vical.saga.ledger import reset_saga_ledger_for_tests
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore


@pytest.fixture()
def env_paths(tmp_path: Path, monkeypatch):
    store_path = tmp_path / "vical.json"
    saga_path = tmp_path / "saga.sqlite"
    monkeypatch.setenv("KEPRIX_VICAL_SAGA_DB_PATH", str(saga_path))
    monkeypatch.setenv("KEPRIX_VICAL_CALENDAR_DB_PATH", str(saga_path))
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("KEPRIX_GOOGLE_CALENDAR_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN", "caltok")
    reset_saga_ledger_for_tests(saga_path)
    reset_projection_store_for_tests(saga_path)
    clear_outbox()
    store = VicalStore(path=store_path)
    ensure_default_consultation("host1", store=store)
    return {"store": store, "saga": saga_path}


def _next_weekday_slot() -> datetime:
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    while start.weekday() > 4:
        start += timedelta(days=1)
    return start


def test_ce_ics_host_and_guest_invitation_evidenced_separately(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot()
    ledger = reset_saga_ledger_for_tests(env_paths["saga"])
    proj = reset_projection_store_for_tests(env_paths["saga"])
    deps = SagaDeps(
        store=store,
        ledger=ledger,
        skip_calendar=False,
        calendar_deps=CalendarSyncDeps(store=proj, ledger=ledger),
    )
    # Avoid Zoom path noise
    result = book_with_saga(
        "host1",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="cal-ics-1",
        prefer_managed_zoom=False,
        meeting_url="https://meet.example/room",
        deps=deps,
    )
    inv = result["invitation"]
    assert inv["hostEventCreated"] is True
    assert inv["invitationSendRequested"] is True
    assert inv["icsFallback"] is True
    assert inv["provider"] == "ics"
    attempts = result["calendar"]["deliveryAttempts"]
    channels = {a["channel"] for a in attempts}
    assert "host_calendar_event" in channels
    assert "guest_invitation" in channels
    assert "email_outbox" in channels
    assert any(a["evidence"] and a["evidence"].startswith("outbox:") for a in attempts)


def test_google_create_separates_host_and_invite_send(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot()
    captured: list[dict] = []

    def fake_fetch(url: str, init: dict):
        captured.append({"url": url, "init": init})
        assert "sendUpdates=all" in url
        return {
            "status": 200,
            "headers": {},
            "json": {
                "id": "gcal-1",
                "etag": "etag-1",
                "htmlLink": "https://calendar.google.com/event?eid=1",
                "attendees": [{"email": "pat@example.com", "responseStatus": "needsAction"}],
            },
        }

    google = GoogleCalendarAdapter(
        fetch_impl=fake_fetch,
        get_access_token=lambda ws, uid: "atok",
        create_cache={},
    )
    ledger = reset_saga_ledger_for_tests(env_paths["saga"])
    proj = reset_projection_store_for_tests(env_paths["saga"])
    deps = SagaDeps(
        store=store,
        ledger=ledger,
        calendar_deps=CalendarSyncDeps(google=google, store=proj, ledger=ledger, prefer_provider="google"),
    )
    # Force google path via injected adapter even without OAuth env
    result = book_with_saga(
        "host1",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="cal-g-1",
        prefer_managed_zoom=False,
        meeting_url="https://zoom.us/j/1",
        deps=deps,
    )
    assert result["invitation"]["provider"] == "google"
    assert result["invitation"]["hostEventCreated"] is True
    assert result["invitation"]["invitationSendRequested"] is True
    assert result["invitation"]["guestResponse"] in {"needsAction", "unknown"}


def test_guest_response_accepted_declined_tentative(env_paths) -> None:
    proj = reset_projection_store_for_tests(env_paths["saga"])
    proj.upsert_projection(
        workspace_id="host1",
        user_id="host1",
        booking_id="b1",
        provider="google",
        provider_event_id="ev1",
        host_event_created=True,
        invitation_send_requested=True,
        invitation_delivery_state="sent",
        attendees=[{"email": "g@example.com", "responseStatus": "needsAction", "deliveryState": "sent"}],
        status="succeeded",
    )
    for status, expected in (
        ("accepted", "accepted"),
        ("declined", "declined"),
        ("tentative", "tentative"),
    ):
        out = apply_attendee_responses(
            workspace_id="host1",
            booking_id="b1",
            provider="google",
            attendees=[{"email": "g@example.com", "responseStatus": status}],
            store=proj,
        )
        assert out["invitation"]["guestResponse"] == expected
        assert out["invitation"]["invitationDeliveryState"] == expected


def test_dst_timezone_passed_to_google(env_paths) -> None:
    bodies: list[dict] = []

    def fake_fetch(url: str, init: dict):
        bodies.append(init.get("body") or {})
        return {
            "status": 200,
            "json": {"id": "dst1", "attendees": []},
            "headers": {},
        }

    google = GoogleCalendarAdapter(
        fetch_impl=fake_fetch,
        get_access_token=lambda ws, uid: "t",
        create_cache={},
    )
    # America/New_York spring forward window material
    starts = datetime(2026, 3, 8, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    ends = starts + timedelta(minutes=30)
    from keprix.vical.types import VcalBooking

    booking = VcalBooking(
        id="dstb",
        user_id="host1",
        event_type_id="et",
        host_user_id="host1",
        guest_name="D",
        guest_email="d@example.com",
        starts_at=starts.astimezone(timezone.utc),
        ends_at=ends.astimezone(timezone.utc),
        status="confirmed",
        guest_token="tok",
        workspace_id="host1",
        meeting_url="https://x",
    )
    ledger = reset_saga_ledger_for_tests(env_paths["saga"])
    proj = reset_projection_store_for_tests(env_paths["saga"])
    project_booking_calendar(
        booking,
        workspace_id="host1",
        deps=CalendarSyncDeps(
            google=google,
            store=proj,
            ledger=ledger,
            prefer_provider="google",
        ),
    )
    assert bodies
    assert "dateTime" in bodies[0]["start"]


def test_conflict_and_rate_limit_action_required(env_paths) -> None:
    store: VicalStore = env_paths["store"]
    starts = _next_weekday_slot()

    def rate_limited(url: str, init: dict):
        return {"status": 429, "json": {}, "headers": {"Retry-After": "2"}}

    google = GoogleCalendarAdapter(
        fetch_impl=rate_limited,
        get_access_token=lambda ws, uid: "t",
        create_cache={},
    )
    ledger = reset_saga_ledger_for_tests(env_paths["saga"])
    proj = reset_projection_store_for_tests(env_paths["saga"])
    result = book_with_saga(
        "host1",
        guest_name="R",
        guest_email="r@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="cal-rate",
        prefer_managed_zoom=False,
        meeting_url="https://x",
        deps=SagaDeps(
            store=store,
            ledger=ledger,
            calendar_deps=CalendarSyncDeps(
                google=google,
                store=proj,
                ledger=ledger,
                prefer_provider="google",
            ),
        ),
    )
    assert result["actionRequired"] is True

    def conflict(url: str, init: dict):
        return {"status": 409, "json": {"error": {"message": "conflict"}}, "headers": {}}

    google2 = GoogleCalendarAdapter(
        fetch_impl=conflict, get_access_token=lambda ws, uid: "t", create_cache={}
    )
    from keprix.vical.calendar.types import CalendarEventInput

    r = google2.create_event(
        CalendarEventInput(
            workspace_id="host1",
            user_id="host1",
            booking_id="bx",
            summary="x",
            starts_at=starts.isoformat().replace("+00:00", "Z"),
            ends_at=(starts + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            idempotency_key="conf-1",
            guest_email="a@b.c",
        )
    )
    assert r.error_code == "conflict"
    assert r.status == "action_required"


def test_duplicate_webhook_and_expiry_renewal(env_paths, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_CONCIERGE_GOOGLE_CALENDAR_WEBHOOK_TOKEN", "caltok")
    reset_saga_ledger_for_tests(env_paths["saga"])
    proj = reset_projection_store_for_tests(env_paths["saga"])
    assert verify_google_calendar_webhook(channel_token="caltok", channel_id="ch1") is True
    assert verify_google_calendar_webhook(channel_token="nope", channel_id="ch1") is False

    headers = {
        "X-Goog-Channel-ID": "ch1",
        "X-Goog-Resource-ID": "res1",
        "X-Goog-Resource-State": "exists",
        "X-Goog-Message-Number": "1",
        "X-Goog-Channel-Token": "caltok",
        "X-Keprix-Workspace-Id": "host1",
        "X-Keprix-Booking-Id": "b1",
    }
    proj.upsert_projection(
        workspace_id="host1",
        user_id="host1",
        booking_id="b1",
        provider="google",
        provider_event_id="ev1",
        host_event_created=True,
        invitation_send_requested=True,
        invitation_delivery_state="sent",
        attendees=[{"email": "g@example.com", "responseStatus": "needsAction", "deliveryState": "sent"}],
        status="succeeded",
    )
    body = {
        "workspaceId": "host1",
        "bookingId": "b1",
        "attendees": [{"email": "g@example.com", "responseStatus": "accepted"}],
    }
    first = handle_google_calendar_webhook(headers=headers, body=body)
    second = handle_google_calendar_webhook(headers=headers, body=body)
    assert first["ok"] and first["duplicate"] is False
    assert second["ok"] and second["duplicate"] is True
    assert first["invitation"]["guestResponse"] == "accepted"

    forged = handle_google_calendar_webhook(
        headers={**headers, "X-Goog-Channel-Token": "bad"}, body=body
    )
    assert forged["ok"] is False

    from datetime import datetime as dt

    soon = (dt.now(timezone.utc) + timedelta(minutes=10)).replace(microsecond=0).isoformat()
    proj.upsert_watch(
        workspace_id="host1",
        user_id="host1",
        provider="google",
        channel_id="watch-1",
        resource_id="r1",
        expiration_at=soon,
    )
    renewed = renew_expiring_watches(
        extend_seconds=86400,
        deps=CalendarSyncDeps(store=proj),
    )
    assert renewed and renewed[0]["renewed"] is True


def test_durable_outbox_not_memory_only(env_paths) -> None:
    clear_outbox()
    proj = reset_projection_store_for_tests(env_paths["saga"])
    from keprix.vical.types import VcalBooking

    booking = VcalBooking(
        id="n1",
        user_id="host1",
        event_type_id="et",
        host_user_id="host1",
        guest_name="N",
        guest_email="n@example.com",
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        status="confirmed",
        guest_token="t",
        workspace_id="host1",
    )
    msg = notify_booking("confirmed", booking, workspace_id="host1")
    assert msg.evidence and msg.evidence.startswith("outbox:")
    assert msg.outbox_id
    pending = proj.list_pending_notifications()
    # marked sent, so not pending
    assert all(p["id"] != msg.outbox_id for p in pending)
    assert any(m.booking_id == "n1" for m in list_outbox())


def test_ics_attendee_and_parseable(env_paths) -> None:
    from keprix.vical.types import VcalBooking
    from keprix.vical.ics import ics_is_parseable

    booking = VcalBooking(
        id="ics1",
        user_id="host1",
        event_type_id="et",
        host_user_id="host1",
        guest_name="Guest",
        guest_email="guest@example.com",
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        status="confirmed",
        guest_token="t",
    )
    body = render_booking_ics(booking, title="Meet")
    assert ics_is_parseable(body)
    assert "ATTENDEE" in body
    assert "guest@example.com" in body
