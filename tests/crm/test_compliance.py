"""Consent / suppression compliance tests (prompt 448)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_suppressed_never_enrolled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm.store import CrmStore
    from keprix.outreach.store import OutreachStore
    from keprix.outreach.service import OutreachService
    from keprix.crm.enroll import enroll_list
    from keprix.crm.compliance import evaluate_send_policy, suppress_address

    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    cstore = CrmStore(tmp_path / "c.db")
    ostore = OutreachStore(tmp_path / "o.db")
    svc = OutreachService(ostore)
    ws = "ws448"
    lead = cstore.create_lead(ws, name="X", email="x@example.com", stage="listed")
    suppress_address(cstore, ws, address="x@example.com", reason="unsubscribe", permanent=True)
    decision = evaluate_send_policy(
        cstore,
        ws,
        subject_type="lead",
        subject_id=lead["id"],
        channel="email",
        address="x@example.com",
    )
    assert decision["decision"] == "deny"

    lst = cstore.create_list(ws, name="Cold")
    cstore.add_list_member(ws, lst["id"], member_type="lead", member_id=lead["id"])
    seq = svc.create_sequence(ws, "S", steps=[{"body": "hi", "delay_hours": 0}])
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
    assert result["enrolled_count"] == 0
    assert result["skipped"]["suppressed"] == 1


def test_approval_to_send_race_suppression(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from keprix.crm.store import CrmStore
    from keprix.outreach.store import OutreachStore
    from keprix.outreach.service import OutreachService
    from keprix.crm.enroll import enroll_list, preflight_crm_list_enroll
    from keprix.crm.compliance import suppress_address

    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    cstore = CrmStore(tmp_path / "c.db")
    ostore = OutreachStore(tmp_path / "o.db")
    svc = OutreachService(ostore)
    ws = "ws448r"
    lead = cstore.create_lead(ws, name="Y", email="y@example.com", stage="listed")
    lst = cstore.create_list(ws, name="Race")
    cstore.add_list_member(ws, lst["id"], member_type="lead", member_id=lead["id"])
    seq = svc.create_sequence(ws, "S", steps=[{"body": "hi", "delay_hours": 0}])
    report = preflight_crm_list_enroll(
        workspace_id=ws,
        list_id=lst["id"],
        sequence_id=seq["id"],
        crm_store=cstore,
        outreach_store=ostore,
    )
    assert report["counts"]["eligible"] == 1
    # Race: suppress after preflight / Soft Wall approve
    suppress_address(cstore, ws, address="y@example.com", reason="unsubscribe")
    result = enroll_list(
        workspace_id=ws,
        list_id=lst["id"],
        sequence_id=seq["id"],
        audience_hash=report["audience_hash"],
        require_soft_wall=False,
        force=True,
        crm_store=cstore,
        outreach_store=ostore,
        outreach_service=svc,
    )
    assert result["enrolled_count"] == 0
    # Re-preflight moves the address into suppressed; race path or suppressed skip both prove suppression wins.
    assert result["skipped"]["suppressed"] >= 1 or any(
        s.get("reason") == "suppressed_at_send" for s in result.get("skipped_race") or []
    )


def test_prohibited_targeting() -> None:
    from keprix.crm.compliance import check_prohibited_targeting

    bad = check_prohibited_targeting({"query": "NHS patient list for cold email"})
    assert bad["allowed"] is False
    good = check_prohibited_targeting({"query": "plumbers in Leeds"})
    assert good["allowed"] is True


def test_docs_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / "docs/features/crm-compliance.md").is_file()
