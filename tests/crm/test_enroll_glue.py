"""Tests for CRM list enroll Soft Wall glue (prompt 442)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def stores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from keprix.crm.store import CrmStore
    from keprix.outreach.store import OutreachStore
    from keprix.outreach.service import OutreachService

    cstore = CrmStore(tmp_path / "crm.db")
    ostore = OutreachStore(tmp_path / "outreach.db")
    svc = OutreachService(ostore)
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")  # allow force path in some tests
    return cstore, ostore, svc


def test_enroll_creates_soft_wall_leads_skips_suppressed(stores) -> None:
    cstore, ostore, svc = stores
    ws = "ws442"
    lead = cstore.create_lead(ws, name="Ann Eligible", email="ann@example.com", stage="listed")
    bad = cstore.create_lead(ws, name="Bob Suppressed", email="bob@example.com", stage="listed")
    cstore.create_suppression_entry(ws, address="bob@example.com", channel="email", reason="unsubscribe")
    lst = cstore.create_list(ws, name="Prospects")
    cstore.add_list_member(ws, lst["id"], member_type="lead", member_id=lead["id"])
    cstore.add_list_member(ws, lst["id"], member_type="lead", member_id=bad["id"])
    seq = svc.create_sequence(
        ws,
        "Nurture",
        steps=[{"subject": "Hi", "body": "Hello {{first_name}}", "delay_hours": 0}],
    )

    from keprix.crm.enroll import enroll_list, preflight_crm_list_enroll

    report = preflight_crm_list_enroll(
        workspace_id=ws,
        list_id=lst["id"],
        sequence_id=seq["id"],
        crm_store=cstore,
        outreach_store=ostore,
    )
    assert report["counts"]["eligible"] == 1
    assert report["counts"]["suppressed"] == 1
    assert report["audience_hash"]

    result = enroll_list(
        workspace_id=ws,
        list_id=lst["id"],
        sequence_id=seq["id"],
        require_soft_wall=False,
        force=True,
        crm_store=cstore,
        outreach_store=ostore,
        outreach_service=svc,
    )
    assert result["blocked"] is False
    assert result["enrolled_count"] == 1
    olead = ostore.find_lead_by_email(ws, "ann@example.com")
    assert olead is not None
    # Bidirectional CRM id in metadata
    from keprix.crm.enroll import _ensure_outreach_metadata_column

    _ensure_outreach_metadata_column(ostore)
    row = ostore.get_lead(ws, olead["id"])
    meta_raw = row.get("metadata_json") or ""
    assert "crm_lead_id" in meta_raw or lead["id"] in meta_raw


def test_audience_hash_mismatch_blocks(stores) -> None:
    cstore, ostore, svc = stores
    ws = "ws442b"
    lead = cstore.create_lead(ws, name="C", email="c@example.com")
    lst = cstore.create_list(ws, name="L")
    cstore.add_list_member(ws, lst["id"], member_type="lead", member_id=lead["id"])
    seq = svc.create_sequence(ws, "S", steps=[{"body": "x", "delay_hours": 0}])
    from keprix.crm.enroll import enroll_list

    result = enroll_list(
        workspace_id=ws,
        list_id=lst["id"],
        sequence_id=seq["id"],
        audience_hash="stale",
        require_soft_wall=False,
        force=True,
        crm_store=cstore,
        outreach_store=ostore,
        outreach_service=svc,
    )
    assert result["blocked"] is True
    assert result["error_code"] == "audience_hash_mismatch"
