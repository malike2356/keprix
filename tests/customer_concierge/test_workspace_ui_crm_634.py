"""Standalone UI, CRM mesh, outreach nurture, channels (Prompt 634)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.auth import dependencies as deps
from keprix.customer_concierge.audience.store import reset_audience_store_for_tests
from keprix.customer_concierge.capability_mesh import build_booking_mesh
from keprix.customer_concierge.nurture_orchestration import (
    apply_cancellation_policy,
    no_show_recovery_gate,
    pause_outreach_for_support_case,
)
from keprix.customer_concierge.published_knowledge import reset_knowledge_store_for_tests
from keprix.customer_concierge.routes import public_router, router
from keprix.customer_concierge.store import reset_concierge_store_for_tests
from keprix.customer_concierge.support_cases import reset_support_case_store_for_tests
from keprix.customer_concierge.surface_tools import audience_tool_catalog
from keprix.vical.saga.ledger import reset_saga_ledger_for_tests
from keprix.vical.seed import ensure_default_consultation
from keprix.vical.store import VicalStore
from keprix.vical.types import VcalBooking


@pytest.fixture()
def env(tmp_path: Path, monkeypatch):
    db = tmp_path / "c634.sqlite"
    saga = tmp_path / "saga.sqlite"
    vical = tmp_path / "vical.json"
    monkeypatch.setenv("KEPRIX_CONCIERGE_DB_PATH", str(db))
    monkeypatch.setenv("KEPRIX_VICAL_SAGA_DB_PATH", str(saga))
    monkeypatch.delenv("KEPRIX_CONCIERGE_NOSHOW_RECOVERY_APPROVED", raising=False)
    reset_concierge_store_for_tests(db)
    reset_audience_store_for_tests(db)
    reset_knowledge_store_for_tests(db)
    reset_support_case_store_for_tests(db)
    reset_saga_ledger_for_tests(saga)
    store = VicalStore(path=vical)
    ensure_default_consultation("op1", store=store)
    app = FastAPI()
    app.include_router(router)
    app.include_router(public_router)
    app.dependency_overrides[deps.get_current_user] = lambda: {"id": "op1", "username": "op1"}
    with TestClient(app) as tc:
        yield {"client": tc, "store": store, "db": db}


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
                "channels": {"web": {"enabled": True}, "telegram": {"enabled": False}},
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


def test_operator_surfaces_bookings_channels_analytics(env, monkeypatch) -> None:
    client: TestClient = env["client"]
    store: VicalStore = env["store"]
    monkeypatch.setattr("keprix.vical.store.vical_store", store)
    _publish(client)

    starts = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    while starts.weekday() > 4:
        starts += timedelta(days=1)
    booking = VcalBooking(
        id="b634",
        user_id="op1",
        event_type_id="consultation",
        host_user_id="op1",
        guest_name="Pat",
        guest_email="pat@example.com",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
        status="confirmed",
        guest_token="gtok",
        workspace_id="op1",
        metadata={"workspace_id": "op1", "crm_lead_id": "lead1", "outreach_lead_id": "olead1"},
        meeting_url="https://zoom.us/j/1",
    )
    store.bookings[booking.id] = booking
    store._guest_token_index[booking.guest_token] = booking.id  # type: ignore[attr-defined]
    store._persist()  # type: ignore[attr-defined]

    books = client.get("/api/customer-concierge/bookings")
    assert books.status_code == 200
    body = books.json()
    assert body["oneRecordSet"] is True
    assert any(b["id"] == "b634" for b in body["bookings"])
    assert body["spreadsheetRows"]

    mesh = client.get("/api/customer-concierge/bookings/b634/mesh")
    assert mesh.status_code == 200
    chain_keys = {c["key"] for c in mesh.json()["mesh"]["chain"]}
    assert "booking" in chain_keys
    assert "lead" in chain_keys
    assert "outreachLead" in chain_keys

    ch = client.get("/api/customer-concierge/channels?personaId=default")
    assert ch.status_code == 200
    assert ch.json()["published"] is True
    assert any(c["key"] == "web" and c["enabled"] for c in ch.json()["channels"])

    patched = client.patch(
        "/api/customer-concierge/channels?personaId=default",
        json={"channels": {"telegram": {"enabled": True}}},
    )
    assert patched.status_code == 200
    assert any(c["key"] == "telegram" and c["enabled"] for c in patched.json()["channels"])

    analytics = client.get("/api/customer-concierge/analytics?personaId=default")
    assert analytics.status_code == 200
    assert analytics.json()["privacySafe"] is True
    assert analytics.json()["includesMessageBodies"] is False
    assert analytics.json()["metrics"]["bookingsTotal"] >= 1

    tools = client.get("/api/customer-concierge/audience-tools?surface=tui")
    assert tools.status_code == 200
    assert tools.json()["ownerPrivileges"] is False
    assert "vical-booking-create" in tools.json()["allowedTools"]
    assert "shell-exec" not in tools.json()["allowedTools"]


def test_mesh_one_record_and_nurture_gates() -> None:
    booking = VcalBooking(
        id="b1",
        user_id="ws",
        event_type_id="et",
        host_user_id="ws",
        guest_name="A",
        guest_email="a@example.com",
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        status="confirmed",
        guest_token="t",
        metadata={"workspace_id": "ws", "crm_contact_id": "c1", "campaign_id": "camp1"},
    )
    mesh = build_booking_mesh(booking, workspace_id="ws", audience_session_id="sess1")
    assert mesh["mesh"]["oneRecord"] is True
    assert mesh["spreadsheetRow"]["crmContactId"] == "c1"
    assert mesh["spreadsheetRow"]["audienceSessionId"] == "sess1"

    cancel = apply_cancellation_policy(booking)
    assert cancel["autoRestartCadence"] is False
    assert cancel["policy"] == "hold"

    denied = no_show_recovery_gate(approved_automation=False)
    assert denied["ok"] is False
    allowed = no_show_recovery_gate(approved_automation=True)
    assert allowed["ok"] is True

    catalog = audience_tool_catalog(surface="gateway")
    assert catalog["workspaceMember"] is False
    assert catalog["denyByDefault"] is True


def test_pause_outreach_on_support_case(env, monkeypatch) -> None:
    """When Soft Wall lead exists, support case pauses cadence."""
    from keprix.outreach.store import get_outreach_store, reset_outreach_store_for_tests

    path = env["db"].parent / "outreach.sqlite"
    monkeypatch.setenv("KEPRIX_OUTREACH_DB_PATH", str(path))
    reset_outreach_store_for_tests(path)
    store = get_outreach_store()
    added = store.add_leads(
        "op1",
        [{"email": "pat@example.com", "status": "contacted", "first_name": "Pat"}],
    )
    lead_id = added[0]["id"] if added else None
    if not lead_id:
        pytest.skip("outreach add_leads unavailable")
    out = pause_outreach_for_support_case(
        workspace_id="op1",
        guest_email="pat@example.com",
        support_case_id="case1",
    )
    assert out.get("paused") is True
    assert out.get("outreachLeadId") == lead_id
