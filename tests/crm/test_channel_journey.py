"""Channel journey sheet → list → Soft Wall campaign (Prompt 627)."""

from __future__ import annotations

import pytest

from keprix.crm.channel_journey import run_channel_journey
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def stores(tmp_path, monkeypatch):
    outreach = reset_outreach_store_for_tests(tmp_path / "outreach.db")
    reset_outreach_ops_store_for_tests(tmp_path / "outreach.db")
    crm = reset_crm_store_for_tests(tmp_path / "crm.db")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: crm)
    monkeypatch.setattr("keprix.outreach.store.get_outreach_store", lambda: outreach)
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_SHEET_PREPROCESS_DIR", str(tmp_path / "sheets"))
    return crm, outreach


def test_sheet_bytes_to_list_and_soft_wall_campaign(stores):
    crm, _outreach = stores
    csv_bytes = b"company_name,email\nAcme Ltd,acme@example.com\nBeta Co,beta@example.com\n"
    result = run_channel_journey(
        "ws_j1",
        payload=csv_bytes,
        filename="leads.csv",
        channel="telegram",
        list_name="Journey list",
        skip_enrich=True,
        crm_store=crm,
    )
    assert result.get("ok") is True
    assert result.get("list_id")
    assert result.get("campaign_id")
    steps = {s["step"]: s for s in result.get("steps") or []}
    assert steps["ingest"]["status"] == "completed"
    assert steps["add_to_list"]["status"] == "completed"
    assert steps["draft_campaign"]["status"] in {"blocked", "approved"}
    # Soft Wall should park enroll without force
    assert result.get("status") in {"waiting_approval", "completed"}
    members = crm.list_memberships("ws_j1", result["list_id"])
    assert len(members) >= 1


def test_workspace_isolation(stores):
    crm, _ = stores
    csv_bytes = b"company_name,email\nOnly A,a@example.com\n"
    run_channel_journey(
        "ws_a",
        payload=csv_bytes,
        filename="a.csv",
        channel="telegram",
        skip_enrich=True,
        crm_store=crm,
    )
    leads_b = crm.list_leads("ws_b", limit=100)
    assert leads_b == []
    leads_a = crm.list_leads("ws_a", limit=100)
    assert any("a@example.com" in str(l.get("emails")) for l in leads_a)
