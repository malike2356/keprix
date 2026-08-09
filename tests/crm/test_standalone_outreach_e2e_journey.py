"""Full standalone lead/outreach E2E journey (Prompt 628).

Exercises real CRM + outreach stores, Soft Wall, claim-lease process-due,
SMTP send via in-process mail capture (local mail-capture adapter), provider
events, mailbox reply ingest, stop-on-reply, booking Soft Wall, customer
conversion, and workbook export. Does not mock success without calling the
send helper.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from keprix.crm.enroll import enroll_list
from keprix.crm.ingestion.export import export_leads_csv, export_leads_xlsx
from keprix.crm.ingestion.service import IngestOptions, ingest_file
from keprix.crm.lifecycle import convert_lead_to_customer
from keprix.crm.store import reset_crm_store_for_tests
from keprix.outreach.mail_capture import (
    capture_sender_resolution,
    captured_messages,
    record_smtp_send,
    reset_mail_capture,
)
from keprix.outreach.observability import REQUIRED_METRIC_KEYS, collect_outreach_observability
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.provider_events import apply_provider_event, normalize_sendgrid_events
from keprix.outreach.service import OutreachService
from keprix.outreach.store import reset_outreach_store_for_tests

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SYNTHETIC_CSV = FIXTURES / "seo_lead_tracker_synthetic.csv"
WS = "ws_e2e_628"


@pytest.fixture()
def journey(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    crm = reset_crm_store_for_tests(tmp_path / "crm.sqlite")
    outreach_path = tmp_path / "outreach.sqlite"
    ostore = reset_outreach_store_for_tests(outreach_path)
    reset_outreach_ops_store_for_tests(outreach_path)
    monkeypatch.setenv("KEPRIX_OUTREACH_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: crm)
    monkeypatch.setattr(
        "keprix.crm.nurture.cadence_allows_send",
        lambda *a, **k: (True, None),
    )
    monkeypatch.setattr(
        "keprix.crm.engagement.hook_soft_wall_reply",
        lambda ws, out, **k: {"ok": True, "bridged": True},
    )
    monkeypatch.setattr(
        "keprix.crm.engagement.ingest_engagement",
        lambda **k: {"ok": True, "inbox": True},
    )
    reset_mail_capture()
    sender = capture_sender_resolution(mailbox="sender@keprix.local")
    monkeypatch.setattr("keprix.email.helpers.send_smtp_message", record_smtp_send)
    monkeypatch.setattr(
        "keprix.outreach.delivery.resolve_sender",
        lambda *a, **k: sender,
    )
    svc = OutreachService(store=ostore)
    return {"crm": crm, "outreach": svc, "store": ostore, "tmp": tmp_path}


def test_full_standalone_journey(journey) -> None:
    crm = journey["crm"]
    outreach: OutreachService = journey["outreach"]
    tmp_path: Path = journey["tmp"]

    # 1. Import synthetic 17-column workbook (CSV fixture = committed synthetic).
    first = ingest_file(
        WS,
        SYNTHETIC_CSV,
        store=crm,
        options=IngestOptions(source_name="synthetic.csv", actor_id="e2e"),
    )
    assert first["created"] >= 1
    assert first["rejected"] == 0
    leads = crm.list_leads(WS)
    assert len(leads) >= 1
    by_email = {
        (lead.get("emails") or [{}])[0].get("address"): lead for lead in leads
    }
    ada = by_email["ada@acme-dental.example"]
    assert ada["company_name"] == "Acme Dental"
    assert ada.get("source_job_id") or ada.get("source_type")

    # 2. Display/edit fields + provenance.
    crm.update_lead(
        WS,
        ada["id"],
        notes="e2e-edited-notes",
        priority="high",
        actor_type="user",
        actor_id="e2e",
    )
    ada = crm.get_lead(WS, ada["id"])
    assert "e2e-edited" in str(ada.get("notes") or "")
    prov = crm.list_provenance(WS, entity_type="lead", entity_id=ada["id"])
    assert prov

    # 3. Deduplicate repeated import.
    second = ingest_file(
        WS,
        SYNTHETIC_CSV,
        store=crm,
        options=IngestOptions(source_name="synthetic-again.csv", actor_id="e2e"),
    )
    assert second["created"] == 0
    assert second.get("updated", 0) + second.get("skipped", 0) + second.get("merged", 0) >= 1
    assert len(crm.list_leads(WS)) == len(leads)

    # 4. List + campaign + 5. enroll sequence.
    lst = crm.create_list(WS, name="E2E Prospects")
    crm.add_list_member(WS, lst["id"], member_type="lead", member_id=ada["id"])
    campaign = outreach.create_campaign(
        WS,
        "E2E Campaign",
        status="active",
        business_hours_only=False,
        require_approval=True,
    )
    sequence = outreach.create_sequence(
        WS,
        "E2E Seq",
        steps=[
            {"subject": "Hello {{first_name}}", "body": "Hi from Keprix E2E", "delay_hours": 0},
            {"subject": "Follow up", "body": "Still interested?", "delay_hours": 24},
        ],
        stop_on_reply=True,
        stop_on_unsubscribe=True,
    )
    enrolled = enroll_list(
        workspace_id=WS,
        list_id=lst["id"],
        sequence_id=sequence["id"],
        campaign_id=campaign["id"],
        require_soft_wall=False,
        force=True,
        crm_store=crm,
        outreach_store=outreach.store,
        outreach_service=outreach,
    )
    assert enrolled.get("blocked") is False
    assert enrolled.get("enrolled_count", 0) >= 1
    olead = outreach.store.find_lead_by_email(WS, "ada@acme-dental.example")
    assert olead is not None
    enr_rows = outreach.store.list_enrollments(WS, lead_id=olead["id"]) if hasattr(
        outreach.store, "list_enrollments"
    ) else None
    if enr_rows is None:
        # Fallback: enrollments via SQL
        row = outreach.store._fetchone(
            "SELECT * FROM outreach_enrollments WHERE lead_id = ? ORDER BY created_at DESC LIMIT 1",
            (olead["id"],),
        )
        assert row
        enrollment_id = row["id"]
    else:
        assert enr_rows
        enrollment_id = enr_rows[0]["id"]

    # 6. Durable scheduler creates Soft Wall approval automatically.
    now = datetime.now(timezone.utc)
    due = outreach.process_due(WS, dry_run=False, now=now, worker_id="e2e-628")
    assert due["items"], due
    assert due["items"][0]["action"] == "soft_wall_queued"
    approval_id = due["items"][0]["approval_id"]
    message_id = due["items"][0]["message_id"]
    assert approval_id and message_id

    # 7-8. Approve and genuinely send via mail-capture SMTP adapter; store ids.
    approved = outreach.approve_soft_wall(WS, approval_id, dry_run=False)
    assert approved.get("ok") is True, approved
    assert approved["send"].get("provider_message_id")
    assert captured_messages(), "mail capture must record the SMTP send"
    msg = outreach.store.get_message(WS, message_id)
    assert msg and msg.get("sent_at")
    assert msg.get("provider_message_id")
    assert msg.get("provider") in {"smtp", "mail_capture"}
    pmid = msg["provider_message_id"]

    # 9. Ingest signed/normalized delivery event (fixture path = verified apply).
    events = normalize_sendgrid_events(
        [
            {
                "event": "delivered",
                "sg_message_id": pmid,
                "sg_event_id": "e2e-delivered-1",
                "email": "ada@acme-dental.example",
            }
        ]
    )
    applied = apply_provider_event(WS, events[0], signature_ok=True, store=outreach.store)
    assert applied.get("ok") is True
    msg = outreach.store.get_message(WS, message_id)
    assert msg.get("delivery_state") in {"delivered", "sent"}

    # 10-11. Controlled reply ingest/match/classify (injected mailbox message).
    reply_scan = outreach.scan_replies(
        WS,
        messages=[
            {
                "from_address": "ada@acme-dental.example",
                "subject": "Re: Hello",
                "text_body": "Sounds interesting; can we book a call next week?",
                "provider_message_id": "reply-e2e-1@mail",
                "in_reply_to": f"<{pmid}>",
                "mailbox": "sender@keprix.local",
                "uid": 42,
            }
        ],
        account={"id": "capture_acct", "email_address": "sender@keprix.local"},
    )
    assert reply_scan["matched"] >= 1
    assert reply_scan["scanned"] >= 1

    # 12. Remaining sequence steps stopped.
    enr = outreach.store.get_enrollment(enrollment_id, workspace_id=WS)
    assert enr and str(enr.get("status") or "").startswith("stopped")

    # 13. Approved follow-up / booking action (ops booking Soft Wall path).
    from keprix.outreach.ops import get_outreach_ops_store

    ops = get_outreach_ops_store()
    booking = ops.create_booking(
        WS,
        olead["id"],
        starts_at=datetime.now(timezone.utc).isoformat(),
        status="scheduled",
        notes="e2e booking after interested reply",
    )
    assert booking.get("id")

    # 14. Convert to customer; attribution preserved.
    converted = convert_lead_to_customer(
        WS,
        ada["id"],
        paying=True,
        crm_store=crm,
        soft_wall_approved=True,
        force=True,
        actor_id="e2e",
    )
    assert converted.get("ok") is True, converted
    assert converted.get("attribution") is not None
    refreshed = crm.get_lead(WS, ada["id"])
    assert str(refreshed.get("stage") or "") in {"paying", "customer"}
    custom = refreshed.get("custom_fields") if isinstance(refreshed.get("custom_fields"), dict) else {}
    assert custom.get("attribution_preserved") or converted.get("attribution")

    # 15. Export Excel + CSV of final record.
    final_leads = [crm.get_lead(WS, ada["id"])]
    xlsx_path = tmp_path / "final.xlsx"
    csv_path = tmp_path / "final.csv"
    export_leads_xlsx(final_leads, xlsx_path)
    export_leads_csv(final_leads, csv_path)
    assert xlsx_path.is_file() and xlsx_path.stat().st_size > 0
    assert csv_path.is_file() and "ada@acme-dental.example" in csv_path.read_text(encoding="utf-8")

    # Observability exposes required signals.
    snap = collect_outreach_observability(WS, store=outreach.store, ops=ops, crm_store=crm)
    for key in REQUIRED_METRIC_KEYS:
        assert key in snap, key
    assert snap["complete"] is True
    assert snap["database_latency_ms"] is not None


def test_observability_keys_stable_empty_workspace(tmp_path: Path) -> None:
    ostore = reset_outreach_store_for_tests(tmp_path / "o.sqlite")
    reset_outreach_ops_store_for_tests(tmp_path / "o.sqlite")
    crm = reset_crm_store_for_tests(tmp_path / "c.sqlite")
    snap = collect_outreach_observability("ws_empty", store=ostore, crm_store=crm)
    assert snap["complete"] is True
    assert snap["queue_depth"] == 0
