"""Nurture stage machine tests (prompt 444)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_transition_graph_and_illegal_skip() -> None:
    from keprix.crm.stages import can_transition, transition_graph

    graph = transition_graph()
    assert "discovered" in graph["forward"]
    assert "paying" in graph["forward"]

    ok, code = can_transition("discovered", "enrolled")
    assert ok is False
    assert code == "illegal_stage_skip"

    ok2, _ = can_transition("discovered", "enriched")
    assert ok2 is True

    ok3, code3 = can_transition("booked", "paying")
    assert ok3 is False
    assert code3 == "customer_paying_requires_human_or_business_event"

    ok4, _ = can_transition("booked", "customer", human_confirmed=True)
    assert ok4 is True


def test_stop_on_reply_via_engagement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm.store import CrmStore
    from keprix.outreach.store import OutreachStore
    from keprix.outreach.service import OutreachService

    cstore = CrmStore(tmp_path / "c.db")
    ostore = OutreachStore(tmp_path / "o.db")
    svc = OutreachService(ostore)
    ws = "ws444"
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")

    olead = ostore.add_leads(ws, [{"email": "g@example.com", "first_name": "G"}])[0]
    seq = svc.create_sequence(
        ws,
        "N",
        steps=[
            {"body": "a", "delay_hours": 0},
            {"body": "b", "delay_hours": 24},
        ],
        stop_on_reply=True,
    )
    svc.enroll_lead(ws, olead["id"], seq["id"])
    crm_lead = cstore.create_lead(ws, name="G", email="g@example.com", stage="enrolled")
    # stamp metadata
    from keprix.crm.enroll import _stamp_lead_metadata

    _stamp_lead_metadata(ostore, ws, olead["id"], {"crm_lead_id": crm_lead["id"]})

    result = svc.classify_and_apply_reply(
        ws,
        from_address="g@example.com",
        body="Interested, let's talk",
        subject="Re",
        classification="interested",
        confidence=0.95,
    )
    assert result["stopped_enrollments"]
    assert result.get("crm")


def test_default_nurture_sequence(tmp_path: Path) -> None:
    from keprix.outreach.store import OutreachStore
    from keprix.outreach.service import OutreachService
    from keprix.crm.nurture import ensure_default_nurture_sequence, list_workflows

    ostore = OutreachStore(tmp_path / "o.db")
    svc = OutreachService(ostore)
    ws = "ws444n"
    created = ensure_default_nurture_sequence(ws, outreach_service=svc, outreach_store=ostore)
    assert created["created"] is True
    assert len(created["sequence"]["steps"]) == 4
    workflows = list_workflows(ws, outreach_store=ostore)
    assert any(w["name"].startswith("Default CRM nurture") for w in workflows)
