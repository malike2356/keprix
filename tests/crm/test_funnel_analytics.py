"""Funnel analytics tests (prompt 447)."""

from __future__ import annotations

from pathlib import Path


def test_funnel_zeros_and_increments(tmp_path: Path) -> None:
    from keprix.crm.store import CrmStore
    from keprix.crm.funnel_analytics import build_digest, funnel_snapshot, record_funnel_event

    store = CrmStore(tmp_path / "c.db")
    ws = "ws447"
    snap = funnel_snapshot(ws, crm_store=store)
    assert snap["metrics"]["leads_discovered"] == 0
    assert snap["metrics"]["enrolled"] == 0

    store.create_lead(ws, name="A", email="a@example.com", stage="enrolled")
    store.create_lead(ws, name="B", email="b@example.com", stage="engaged")
    store.create_lead(ws, name="C", email="c@example.com", stage="booked")
    store.create_list(ws, name="L1")
    record_funnel_event(ws, "enrolled", 1)
    record_funnel_event(ws, "replied", 1)
    record_funnel_event(ws, "booked", 1)

    snap2 = funnel_snapshot(ws, crm_store=store)
    assert snap2["metrics"]["lists_created"] >= 1
    assert snap2["metrics"]["enrolled"] >= 1
    assert snap2["metrics"]["replied"] >= 1
    assert snap2["metrics"]["booked"] >= 1

    digest = build_digest(ws, crm_store=store)
    assert "CRM digest" in digest["message"]
    assert digest["deep_links"]["crm"] == "/crm"
