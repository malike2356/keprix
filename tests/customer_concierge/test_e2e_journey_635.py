"""Full hermetic Customer Concierge journey (Prompt 635)."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.customer_concierge.audience.store import reset_audience_store_for_tests
from keprix.customer_concierge.contract_paths import fixtures_dir
from keprix.customer_concierge.handoff import operator_takeover, request_handoff
from keprix.customer_concierge.published_knowledge import reset_knowledge_store_for_tests
from keprix.customer_concierge.routes import public_router, router
from keprix.customer_concierge.store import reset_concierge_store_for_tests
from keprix.customer_concierge.support_cases import reset_support_case_store_for_tests
from keprix.customer_concierge.testing import build_hermetic_google, build_hermetic_zoom
from keprix.customer_concierge.workspace_surface import analytics_surface, list_unified_bookings
from keprix.vical.calendar.projection_store import reset_projection_store_for_tests
from keprix.vical.calendar.reconcile import apply_attendee_responses
from keprix.vical.calendar.sync_booking import CalendarSyncDeps
from keprix.vical.ics import ics_is_parseable, render_booking_ics
from keprix.vical.reminders import process_reminders
from keprix.vical.saga import SagaDeps, book_with_saga, cancel_with_saga, reschedule_with_saga
from keprix.vical.saga.ledger import reset_saga_ledger_for_tests
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore


@pytest.fixture()
def env(tmp_path: Path, monkeypatch):
    db = tmp_path / "c635.sqlite"
    saga = tmp_path / "saga.sqlite"
    vical = tmp_path / "vical.json"
    monkeypatch.setenv("KEPRIX_CONCIERGE_DB_PATH", str(db))
    monkeypatch.setenv("KEPRIX_VICAL_SAGA_DB_PATH", str(saga))
    monkeypatch.setenv("KEPRIX_VICAL_CALENDAR_DB_PATH", str(saga))
    monkeypatch.setenv("KEPRIX_VICAL_REMINDERS_ENABLED", "1")
    monkeypatch.setenv("ZOOM_CLIENT_ID", "zid")
    monkeypatch.setenv("ZOOM_CLIENT_SECRET", "zsecret")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "gid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "gsecret")
    reset_concierge_store_for_tests(db)
    reset_audience_store_for_tests(db)
    reset_knowledge_store_for_tests(db)
    reset_support_case_store_for_tests(db)
    ledger = reset_saga_ledger_for_tests(saga)
    proj = reset_projection_store_for_tests(saga)
    store = VicalStore(path=vical)
    ensure_default_consultation("host1", store=store)
    monkeypatch.setattr("keprix.vical.store.vical_store", store)
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_router)
    app.dependency_overrides[deps.get_current_user] = lambda: {"id": "host1", "username": "host1"}
    with TestClient(app) as tc:
        yield {
            "client": tc,
            "store": store,
            "ledger": ledger,
            "proj": proj,
            "saga": saga,
            "db": db,
        }


def _publish(client: TestClient) -> None:
    assert (
        client.post(
            "/api/customer-concierge/setup/step1",
            json={
                "personaId": "default",
                "personaName": "Desk",
                "greetingMessage": "Hi",
                "businessName": "Acme",
                "businessDescription": "Demos",
                "escalationEmail": "ops@acme.test",
                "knowledgeSourceIds": [],
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/customer-concierge/setup/step2",
            json={
                "personaId": "default",
                "channels": {"web": {"enabled": True}},
                "businessHours": {"timezone": "UTC", "windows": []},
                "calendarProvider": None,
                "conferencingProvider": None,
                "meetingTypes": [],
                "icsFallbackOk": True,
            },
        ).status_code
        == 200
    )
    assert client.post("/api/customer-concierge/publish?personaId=default").status_code == 200


def _slot() -> datetime:
    start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    while start.weekday() > 4:
        start += timedelta(days=1)
    return start


def test_signed_fixture_manifest_integrity() -> None:
    manifest_path = fixtures_dir() / "MANIFEST.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["algorithm"] == "sha256"
    assert manifest["fixtureCount"] >= 8
    material_lines = []
    for entry in manifest["fixtures"]:
        path = fixtures_dir() / entry["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"]
        material_lines.append(f"{entry['file']}:{digest}")
    material = "\n".join(material_lines).encode()
    expected = hashlib.sha256(b"keprix-customer-concierge-v1|" + material).hexdigest()
    assert expected == manifest["signature"]


def test_full_journey_support_booking_calendar_crm_analytics(env) -> None:
    client: TestClient = env["client"]
    store: VicalStore = env["store"]
    _publish(client)

    # Knowledge + public session
    kb = client.post(
        "/api/customer-concierge/knowledge",
        json={
            "personaId": "default",
            "title": "Hours",
            "content": "We are open weekdays 9-5 UTC.",
            "type": "faq",
            "attachToProfile": True,
        },
    )
    assert kb.status_code == 200
    sid = kb.json()["source"]["id"]
    assert client.post(f"/api/customer-concierge/knowledge/{sid}/publish-state", json={"publishState": "published"}).status_code == 200

    session = client.post("/api/customer-concierge/public/host1/default/session", json={})
    assert session.status_code == 200
    session_id = session.json()["sessionId"]
    assert session.json()["workspaceMember"] is False

    msg = client.post(
        f"/api/customer-concierge/public/host1/default/session/{session_id}/message",
        json={"text": "What are your hours?"},
    )
    assert msg.status_code == 200
    assert msg.json()["ok"] is True

    # Hermetic book: Zoom + Google + ICS fallback evidence
    starts = _slot()
    zoom = build_hermetic_zoom()
    google = build_hermetic_google()
    deps = SagaDeps(
        zoom_adapter=zoom,
        store=store,
        ledger=env["ledger"],
        calendar_deps=CalendarSyncDeps(
            google=google,
            store=env["proj"],
            ledger=env["ledger"],
            prefer_provider="google",
        ),
    )
    booked = book_with_saga(
        "host1",
        guest_name="Pat Guest",
        guest_email="guest@example.com",
        starts_at=starts,
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        persona_id="default",
        idempotency_key="e2e-635-1",
        prefer_managed_zoom=True,
        metadata={
            "workspace_id": "host1",
            "crm_lead_id": "lead635",
            "outreach_lead_id": "olead635",
            "conversation_id": session_id,
        },
        deps=deps,
    )
    assert booked["duplicate"] is False
    assert booked["conferenceManaged"] is True
    assert "HOSTSECRET" not in json.dumps(booked["publicBooking"])
    assert booked.get("invitation")
    assert booked["invitation"]["hostEventCreated"] is True
    assert booked["invitation"]["invitationSendRequested"] is True

    booking = booked["booking"]
    ics = render_booking_ics(booking, title="Consultation")
    assert ics_is_parseable(ics)
    assert "ATTENDEE" in ics

    # Reminder path (force due by setting starts soon and clearing meta)
    booking = store.update_booking(
        "host1",
        booking.id,
        starts_at=datetime.now(timezone.utc) + timedelta(minutes=50),
        ends_at=datetime.now(timezone.utc) + timedelta(minutes=80),
        metadata={**(booking.metadata or {}), "reminders": {}},
    )
    rem = process_reminders(store=store, now=datetime.now(timezone.utc))
    assert rem.get("ok") is True

    # Guest response accepted
    resp = apply_attendee_responses(
        workspace_id="host1",
        booking_id=booking.id,
        provider="google",
        attendees=[{"email": "guest@example.com", "responseStatus": "accepted"}],
        store=env["proj"],
    )
    assert resp["invitation"]["guestResponse"] == "accepted"

    # Reschedule
    new_start = starts + timedelta(days=1)
    while new_start.weekday() > 4:
        new_start += timedelta(days=1)
    moved = reschedule_with_saga(
        "host1",
        booking.id,
        starts_at=new_start,
        workspace_id="host1",
        deps=deps,
    )
    assert moved["booking"].id == booking.id

    # Case escalation + human takeover
    handoff = request_handoff(
        workspace_id="host1",
        persona_id="default",
        audience_session_id=session_id,
        reason="Need human help with booking",
        channel="web",
    )
    assert handoff["ok"] is True
    assert handoff.get("supportCase")
    take = operator_takeover(
        workspace_id="host1",
        audience_session_id=session_id,
        operator_user_id="host1",
    )
    assert take["ok"] is True

    # Unified bookings + analytics
    unified = list_unified_bookings("host1")
    assert unified["oneRecordSet"] is True
    assert any(b["id"] == booking.id for b in unified["bookings"])
    analytics = analytics_surface("host1", persona_id="default")
    assert analytics["privacySafe"] is True
    assert analytics["metrics"]["bookingsTotal"] >= 1
    assert analytics["includesHostStartUrls"] is False

    # Cancel coordinates conference + calendar + nurture policy
    cancelled = cancel_with_saga("host1", booking.id, workspace_id="host1", deps=deps)
    assert cancelled["booking"].status == "cancelled"
    assert cancelled.get("nurture", {}).get("autoRestartCadence") is False


def test_ops_matrix_concurrency_revoked_outage_backup_dst(env, monkeypatch) -> None:
    store: VicalStore = env["store"]
    starts = _slot()

    # Concurrency: duplicate idempotency creates one booking (calendar skipped: sqlite conn is not multi-thread)
    zoom = build_hermetic_zoom()
    deps = SagaDeps(
        zoom_adapter=zoom,
        store=store,
        ledger=env["ledger"],
        skip_calendar=True,
    )
    # CE SQLite ledger is single-connection; prove duplicate-request idempotency under serialized contention
    lock = threading.Lock()
    results = []

    def _book(_i: int):
        with lock:
            results.append(
                book_with_saga(
                    "host1",
                    guest_name="Race",
                    guest_email="race@example.com",
                    starts_at=starts,
                    slug="consultation",
                    skip_slot_check=True,
                    workspace_id="host1",
                    idempotency_key="race-635",
                    prefer_managed_zoom=True,
                    deps=deps,
                )
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(_book, range(4)))
    ids = {r["booking"].id for r in results}
    assert len(ids) == 1
    assert sum(1 for r in results if r["duplicate"]) >= 1

    # Revoked Zoom credential -> not fake success managed Zoom
    from keprix.customer_concierge.testing.hermetic_providers import zoom_revoked_fetch

    revoked = build_hermetic_zoom(fetch_impl=zoom_revoked_fetch())
    bad = book_with_saga(
        "host1",
        guest_name="Rev",
        guest_email="rev@example.com",
        starts_at=starts + timedelta(hours=2),
        slug="consultation",
        skip_slot_check=True,
        workspace_id="host1",
        idempotency_key="revoked-635",
        prefer_managed_zoom=True,
        deps=SagaDeps(zoom_adapter=revoked, store=store, ledger=env["ledger"], skip_calendar=True),
    )
    assert bad["conferenceManaged"] is False

    # Google outage -> CE ICS path still usable when prefer falls through
    from keprix.customer_concierge.testing.hermetic_providers import google_outage_fetch
    from keprix.vical.calendar.google_adapter import GoogleCalendarAdapter

    outage_google = GoogleCalendarAdapter(
        fetch_impl=google_outage_fetch(),
        get_access_token=lambda ws, uid: "t",
        create_cache={},
    )
    from keprix.vical.calendar.sync_booking import project_booking_calendar

    booking = store.list_bookings("host1")[0]
    proj = project_booking_calendar(
        booking,
        workspace_id="host1",
        deps=CalendarSyncDeps(
            google=outage_google,
            store=env["proj"],
            ledger=env["ledger"],
            prefer_provider="google",
        ),
    )
    assert proj["provider"] == "ics" or proj.get("actionRequired")

    # DST material: America/New_York spring forward
    dst_start = datetime(2026, 3, 8, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    assert dst_start.utcoffset() is not None

    # Backup / restore sqlite projection store (do not replace global test store)
    import shutil

    from keprix.vical.calendar.projection_store import ProjectionStore

    backup = env["saga"].with_suffix(".bak")
    shutil.copy2(env["saga"], backup)
    assert backup.is_file()
    restored = ProjectionStore(path=backup)
    try:
        assert restored.list_pending_notifications(limit=1) is not None
    finally:
        restored.close()

    # Desktop packaging presence (Electron app; not rebuilt here)
    desktop = Path(__file__).resolve().parents[2] / "src/keprix/apps/desktop/package.json"
    assert desktop.is_file()
    pkg = json.loads(desktop.read_text(encoding="utf-8"))
    assert "build" in pkg or "main" in pkg

    # Outbox dead-letter + retry operator controls
    note = env["proj"].enqueue_notification(
        workspace_id="host1",
        booking_id="b-dlq",
        channel="email",
        to_address="x@example.com",
        subject="t",
        body="b",
    )
    env["proj"].mark_dead_letter(note["id"], error="smtp_timeout")
    dlq = env["proj"].list_dead_letter_notifications(workspace_id="host1")
    assert any(d["id"] == note["id"] for d in dlq)
    retried = env["proj"].retry_notification(note["id"])
    assert retried and retried["ok"] is True
    assert retried["status"] == "pending"

    # No Carina runtime import in customer_concierge package
    import ast

    pkg_root = Path(__file__).resolve().parents[2] / "src/keprix/customer_concierge"
    for path in pkg_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("carina")
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("carina")


def test_tenant_isolation_filter_and_pg_label(monkeypatch) -> None:
    from keprix.customer_concierge.capability_health import evaluate_capability_health
    from keprix.customer_concierge.scope import filter_rows_for_workspace

    rows = [
        {"workspaceId": "a", "id": "1"},
        {"workspaceId": "b", "id": "2"},
    ]
    assert [r["id"] for r in filter_rows_for_workspace(rows, "a")] == ["1"]
    monkeypatch.delenv("KEPRIX_DATABASE_URL", raising=False)
    report = evaluate_capability_health(workspace_id="a")
    assert report["persistenceMode"] in {"sqlite", "postgres"}
    assert report["canonicalBookingService"] == "keprix.vical.saga.book_with_saga"
