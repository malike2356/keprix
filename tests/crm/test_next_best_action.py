"""Next-best-action suggestions never bypass Soft Wall / suppression (Prompt 627)."""

from __future__ import annotations

import pytest

from keprix.crm.models import CrmStage
from keprix.crm.next_best_action import execute_next_best_action, suggest_next_best_action
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def crm(tmp_path, monkeypatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.db")
    reset_outreach_ops_store_for_tests(tmp_path / "outreach.db")
    store = reset_crm_store_for_tests(tmp_path / "crm.db")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: store)
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    return store


def test_suggestion_shape(crm):
    lead = crm.create_lead(
        "ws",
        name="N",
        emails=[{"address": "n@example.com", "primary": True}],
        stage=CrmStage.ENGAGED,
    )
    suggestion = suggest_next_best_action("ws", subject_id=lead["id"], crm_store=crm)
    assert suggestion.get("ok") is True
    assert suggestion.get("action")
    assert "reason" in suggestion
    assert "confidence" in suggestion
    assert suggestion.get("requires_approval") is True


def test_execute_never_bypasses_soft_wall(crm):
    lead = crm.create_lead(
        "ws",
        name="E",
        emails=[{"address": "e@example.com", "primary": True}],
        stage=CrmStage.QUALIFIED,
    )
    result = execute_next_best_action("ws", subject_id=lead["id"], crm_store=crm)
    assert result.get("blocked") is True
    assert result.get("error_code") in {"soft_wall_required", "soft_wall_pending"}
    assert result.get("approval")


def test_suppressed_blocks_mutating_execute(crm):
    lead = crm.create_lead(
        "ws",
        name="S",
        emails=[{"address": "s@example.com", "primary": True}],
        stage=CrmStage.CONTACTED,
    )
    crm.create_suppression_entry("ws", channel="email", address="s@example.com", reason="opt_out")
    suggestion = suggest_next_best_action("ws", subject_id=lead["id"], crm_store=crm)
    assert suggestion.get("suppressed") is True
    result = execute_next_best_action(
        "ws",
        subject_id=lead["id"],
        action="enrol_sequence",
        force=True,
        crm_store=crm,
    )
    assert result.get("ok") is False
    assert result.get("error_code") == "suppressed"
