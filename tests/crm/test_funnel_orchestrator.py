"""Funnel orchestrator Soft Wall, suppression, and idempotency (Prompt 627)."""

from __future__ import annotations

import pytest

from keprix.crm.funnel_orchestrator import orchestrate
from keprix.crm.models import CrmStage
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def crm(tmp_path, monkeypatch):
    # Ops shares the outreach sqlite so message/approval tables exist.
    reset_outreach_store_for_tests(tmp_path / "outreach.db")
    reset_outreach_ops_store_for_tests(tmp_path / "outreach.db")
    store = reset_crm_store_for_tests(tmp_path / "crm.db")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: store)
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    return store


def test_trigger_idempotency(crm):
    lead = crm.create_lead("ws_a", name="A", emails=[{"address": "a@example.com", "primary": True}])
    first = orchestrate(
        "ws_a",
        trigger="lead_created",
        action="add_tag",
        subject_id=lead["id"],
        idempotency_key="tag-once",
        payload={"tag": "funnel"},
        crm_store=crm,
        require_soft_wall=False,
    )
    assert first.get("ok") is True
    second = orchestrate(
        "ws_a",
        trigger="lead_created",
        action="add_tag",
        subject_id=lead["id"],
        idempotency_key="tag-once",
        payload={"tag": "funnel"},
        crm_store=crm,
        require_soft_wall=False,
    )
    assert second.get("idempotent") is True
    assert second.get("run", {}).get("id") == first.get("run", {}).get("id")


def test_soft_wall_gate_on_high_risk(crm):
    lead = crm.create_lead("ws_a", name="B", emails=[{"address": "b@example.com", "primary": True}])
    result = orchestrate(
        "ws_a",
        trigger="stage_changed",
        action="update_stage",
        subject_id=lead["id"],
        idempotency_key="stage-pay",
        payload={"stage": CrmStage.PAYING},
        crm_store=crm,
        require_soft_wall=True,
    )
    assert result.get("blocked") is True
    assert result.get("error_code") in {"soft_wall_required", "soft_wall_pending"}
    assert result.get("approval")


def test_suppression_blocks_mutating_action(crm):
    lead = crm.create_lead(
        "ws_a",
        name="C",
        emails=[{"address": "c@example.com", "primary": True}],
        stage=CrmStage.CONTACTED,
    )
    crm.create_suppression_entry(
        "ws_a",
        channel="email",
        address="c@example.com",
        reason="unsubscribe",
    )
    result = orchestrate(
        "ws_a",
        trigger="reply_received",
        action="enrol_sequence",
        subject_id=lead["id"],
        idempotency_key="enroll-suppressed",
        payload={"sequence_id": "seq-x"},
        crm_store=crm,
        require_soft_wall=False,
        force=True,
    )
    assert result.get("ok") is False
    assert result.get("error_code") == "suppressed"
