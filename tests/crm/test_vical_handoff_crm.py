"""viCal CRM handoff tests (prompt 445)."""

from __future__ import annotations

from pathlib import Path


def test_confirm_booking_updates_crm(tmp_path: Path) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm.booking import on_vical_booking_confirmed_crm

    store = CrmStore(tmp_path / "c.db")
    ws = "ws445"
    lead = store.create_lead(ws, name="Guest", email="guest@example.com", stage="qualified")
    booking = {
        "id": "bk1",
        "status": "confirmed",
        "guest_email": "guest@example.com",
        "starts_at": "2026-08-10T10:00:00+00:00",
        "ends_at": "2026-08-10T10:30:00+00:00",
        "metadata": {"workspace_id": ws, "crm_lead_id": lead["id"]},
    }
    result = on_vical_booking_confirmed_crm(booking, crm_store=store)
    assert result.get("crm_booking", {}).get("ok") is True
    assert store.get_lead(ws, lead["id"])["stage"] == "booked"
    acts = store.list_activities(ws, entity_type="lead", entity_id=lead["id"])
    assert any(a.get("activity_type") == "booking_confirmed" for a in acts)


def test_missing_vical_host_fails_honestly() -> None:
    from keprix.crm.booking import resolve_booking_link

    result = resolve_booking_link(host_user_id=None, campaign={})
    assert result["ok"] is False
    assert result["reason"] in {"missing_vical_host", "vical_unavailable"}


def test_offer_booking_tool_shape(tmp_path: Path) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm.booking import offer_booking

    store = CrmStore(tmp_path / "c.db")
    ws = "ws445b"
    contact = store.create_contact(ws, "Hosted", email="h@example.com", stage="engaged")
    # Without host profile, may fail honestly or use fallback
    result = offer_booking(ws, contact_id=contact["id"], host_user_id=ws, crm_store=store)
    assert "ok" in result
    if result["ok"]:
        assert result["gui"]["open_crm"].endswith(contact["id"])
