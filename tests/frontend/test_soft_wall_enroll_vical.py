"""Soft Wall list enroll preflight + viCal handoff (prompts 475-476)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_enroll_preflight_skips_suppressed() -> None:
    from keprix.crm.store import CrmStore
    from keprix.outreach.enroll_preflight import preflight_list_enroll
    from keprix.outreach.store import OutreachStore
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    ostore = OutreachStore(tmp / "o.db")
    cstore = CrmStore(tmp / "c.db")
    created = ostore.add_leads("ws", [{"email": "a@example.com", "first_name": "A", "status": "new"}])
    lead = created[0] if isinstance(created, list) else created
    lead_id = lead["id"] if isinstance(lead, dict) else str(lead)
    cstore.create_suppression_entry("ws", address="a@example.com", channel="email", reason="bounce", source="bounce")
    report = preflight_list_enroll(
        workspace_id="ws",
        lead_ids=[lead_id],
        sequence_id="seq1",
        outreach_store=ostore,
        crm_store=cstore,
    )
    assert report["counts"]["suppressed"] == 1
    assert report["counts"]["eligible"] == 0
    assert report["audience_hash"]


def test_list_enroll_routes_and_lists_gui() -> None:
    routes = (ROOT / "src/keprix/outreach/ui_routes.py").read_text(encoding="utf-8")
    assert "/lists/{list_id}/enroll-preflight" in routes
    assert "/lists/{list_id}/enroll" in routes
    assert "audience_hash" in routes
    page = (ROOT / "frontend/src/app/(workspace)/outreach/lists/page.tsx").read_text(encoding="utf-8")
    assert "Soft Wall enroll" in page
    assert "preflightOutreachListEnroll" in page
    api = (ROOT / "frontend/src/lib/outreach-api.ts").read_text(encoding="utf-8")
    assert "enroll-preflight" in api


def test_vical_handoff_wired() -> None:
    bookings = (ROOT / "src/keprix/vical/bookings.py").read_text(encoding="utf-8")
    assert "soft_wall_handoff_on_vical_confirmed" in bookings
    handoff = (ROOT / "src/keprix/outreach/vical_handoff.py").read_text(encoding="utf-8")
    assert "vical_booking_id" in handoff
    page = (ROOT / "frontend/src/app/(workspace)/outreach/bookings/page.tsx").read_text(encoding="utf-8")
    assert "/vical" in page
    assert "source of truth" in page.lower() or "viCal" in page
