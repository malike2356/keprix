"""Automatic mailbox reply scan + thread reconciliation (Prompt 626)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.outreach.inbound_mail import (
    attachment_meta_safe,
    normalize_inbound,
    sanitize_attachment_filename,
)
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.service import OutreachService
from keprix.outreach.store import reset_outreach_store_for_tests


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


@pytest.fixture()
def outreach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OutreachService:
    path = tmp_path / "outreach.sqlite"
    store = reset_outreach_store_for_tests(path)
    reset_outreach_ops_store_for_tests(path)
    monkeypatch.setenv("KEPRIX_OUTREACH_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "1")

    class _Crm:
        suppressed: set[str] = set()
        suppressions: list[dict] = []

        def is_kill_switch_on(self, *a, **k):
            return False

        def is_suppressed(self, ws, channel="email", address=""):
            return str(address or "").lower() in self.suppressed

        def create_suppression_entry(self, ws, **kwargs):
            addr = str(kwargs.get("address") or "").lower()
            self.suppressed.add(addr)
            self.suppressions.append({"workspace_id": ws, **kwargs})
            return {"ok": True}

    crm = _Crm()
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
    svc = OutreachService(store=store)
    svc._test_crm = crm  # type: ignore[attr-defined]
    return svc


def _seed_sent(
    outreach: OutreachService,
    *,
    ws: str = "ws_1",
    email: str = "ada@example.com",
    provider_message_id: str = "out-msg-1@keprix.test",
    provider_thread_id: str | None = "thread-1",
    correlation_id: str | None = "kp-abcde12",
    mailbox: str = "sender@keprix.test",
) -> dict:
    campaign = outreach.create_campaign(
        ws,
        "Mailbox camp",
        status="active",
        business_hours_only=False,
        require_approval=False,
    )
    sequence = outreach.create_sequence(
        ws,
        "seq",
        steps=[{"subject": "Hello", "body": "Hi", "delay_hours": 24}],
        stop_on_reply=True,
        stop_on_unsubscribe=True,
    )
    added = outreach.add_leads(
        ws,
        campaign_id=campaign["id"],
        leads=[{"email": email, "first_name": "Ada", "company": "Analytical"}],
    )
    lead = added["leads"][0]
    enrolled = outreach.enroll_lead(ws, lead["id"], sequence["id"])
    enrollment = enrolled["enrollment"]
    now = _iso(datetime.now(timezone.utc) - timedelta(hours=1))
    message = outreach.store.create_message(
        workspace_id=ws,
        enrollment_id=enrollment["id"],
        subject="Hello",
        body="Hi Ada",
        sent_at=now,
        provider_message_id=provider_message_id,
        provider_thread_id=provider_thread_id,
        correlation_id=correlation_id,
        mailbox=mailbox,
        delivery_state="sent",
    )
    return {
        "campaign": campaign,
        "sequence": sequence,
        "lead": lead,
        "enrollment": enrollment,
        "message": message,
        "workspace_id": ws,
    }


def test_thread_match_via_in_reply_to(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach)
    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "ada@example.com",
            "subject": "Re: Hello",
            "text_body": "Sounds interesting, tell me more",
            "provider_message_id": "in-1@mail",
            "in_reply_to": f"<{seeded['message']['provider_message_id']}>",
            "mailbox": "sender@keprix.test",
        },
    )
    assert result["status"] == "matched"
    assert result["deduped"] is False
    reply = result["reply"]
    assert reply["match_status"] == "matched"
    assert reply["matched_message_id"] == seeded["message"]["id"]
    assert reply["lead_id"] == seeded["lead"]["id"]
    assert result["classified"]["classification"]["classification"] == "interested"
    enr = outreach.store.get_enrollment(seeded["enrollment"]["id"], workspace_id="ws_1")
    assert enr["status"] == "stopped_reply"


def test_references_multi_token_match(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach, provider_message_id="mid-ref@keprix.test")
    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "ada@example.com",
            "subject": "Re: Hello",
            "text_body": "Can we book a call next week?",
            "provider_message_id": "in-ref@mail",
            "references": ["<other@x>", f"<{seeded['message']['provider_message_id']}>"],
            "mailbox": "sender@keprix.test",
        },
    )
    assert result["status"] == "matched"
    assert result["classified"]["classification"]["classification"] == "booking_intent"


def test_cross_workspace_never_matches(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach, ws="ws_a")
    # Same provider_message_id referenced from another workspace must not match
    result = outreach.ingest_inbound_normalized(
        "ws_b",
        {
            "from_address": "ada@example.com",
            "subject": "Re: Hello",
            "text_body": "interested",
            "provider_message_id": "cross-1@mail",
            "in_reply_to": seeded["message"]["provider_message_id"],
        },
    )
    assert result["status"] in ("unmatched", "ambiguous")
    assert result["reply"]["match_status"] != "matched" or result["reply"].get("lead_id") is None
    # Ensure ws_a enrollment still active (no classify applied on ws_b)
    enr = outreach.store.get_enrollment(seeded["enrollment"]["id"], workspace_id="ws_a")
    assert enr["status"] == "active"


def test_ambiguous_needs_review_no_auto_stage(outreach: OutreachService) -> None:
    seeded = _seed_sent(
        outreach,
        provider_message_id="a1@k",
        provider_thread_id="shared-thread",
        correlation_id=None,
    )
    # Second outbound in same workspace sharing provider_thread_id → ambiguous
    campaign2 = outreach.create_campaign("ws_1", "c2", status="active", business_hours_only=False)
    seq2 = outreach.create_sequence(
        "ws_1", "s2", steps=[{"subject": "X", "body": "Y", "delay_hours": 1}]
    )
    added2 = outreach.add_leads(
        "ws_1",
        campaign_id=campaign2["id"],
        leads=[{"email": "bob@example.com", "first_name": "Bob"}],
    )
    lead2 = added2["leads"][0]
    enr2 = outreach.enroll_lead("ws_1", lead2["id"], seq2["id"])["enrollment"]
    outreach.store.create_message(
        workspace_id="ws_1",
        enrollment_id=enr2["id"],
        subject="Other",
        body="Other",
        sent_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=20)),
        provider_message_id="b1@k",
        provider_thread_id="shared-thread",
        mailbox="sender@keprix.test",
        delivery_state="sent",
    )

    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "unknown@example.com",
            "subject": "hi",
            "text_body": "maybe",
            "provider_message_id": "ambig@mail",
            "thread_id": "shared-thread",
            "mailbox": "sender@keprix.test",
        },
    )
    assert result["status"] == "ambiguous"
    assert result["reply"]["review_status"] == "needs_review"
    assert result.get("classified") is None
    lead = outreach.store.get_lead("ws_1", seeded["lead"]["id"])
    assert lead["status"] in ("new", "enrolled", "contacted")


def test_unmatched_stored(outreach: OutreachService) -> None:
    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "stranger@example.com",
            "subject": "Hello",
            "text_body": "Who are you?",
            "provider_message_id": "unmatched-1@mail",
        },
    )
    assert result["status"] == "unmatched"
    assert result["reply"]["match_status"] == "unmatched"
    assert result["reply"]["review_status"] == "needs_review"
    rows = outreach.list_review_queue("ws_1")
    assert any(r["id"] == result["reply"]["id"] for r in rows)


def test_idempotent_rescan_same_message_id(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach)
    payload = {
        "from_address": "ada@example.com",
        "subject": "Re: Hello",
        "text_body": "interested please",
        "provider_message_id": "dup-1@mail",
        "in_reply_to": seeded["message"]["provider_message_id"],
    }
    first = outreach.ingest_inbound_normalized("ws_1", payload)
    second = outreach.ingest_inbound_normalized("ws_1", payload)
    assert first["deduped"] is False
    assert second["deduped"] is True
    assert second["reply"]["id"] == first["reply"]["id"]
    replies = outreach.list_replies("ws_1")
    assert len([r for r in replies if r.get("provider_message_id") == "dup-1@mail"]) == 1


def test_classification_stops_enrollment_unsubscribe(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach)
    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "ada@example.com",
            "subject": "stop",
            "text_body": "Please unsubscribe me from this list",
            "provider_message_id": "unsub-1@mail",
            "in_reply_to": seeded["message"]["provider_message_id"],
        },
    )
    assert result["status"] == "matched"
    assert result["classified"]["classification"]["classification"] == "unsubscribe"
    enr = outreach.store.get_enrollment(seeded["enrollment"]["id"], workspace_id="ws_1")
    assert enr["status"] == "stopped_unsubscribe"
    assert "ada@example.com" in outreach._test_crm.suppressed  # type: ignore[attr-defined]


def test_soft_wall_draft_approval_created(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach)
    result = outreach.ingest_inbound_normalized(
        "ws_1",
        {
            "from_address": "ada@example.com",
            "subject": "Re: Hello",
            "text_body": "Too expensive for us right now, budget concerns",
            "provider_message_id": "obj-1@mail",
            "in_reply_to": seeded["message"]["provider_message_id"],
        },
    )
    assert result["status"] == "matched"
    classified = result["classified"]
    assert classified.get("draft_response")
    approval = classified.get("draft_approval")
    assert approval is not None
    assert approval.get("kind") == "reply_draft" or approval.get("approval_type") == "reply_draft"
    assert approval.get("status") == "pending"


def test_attachment_metadata_only_unsafe_rejected() -> None:
    safe = attachment_meta_safe(filename="quote.pdf", size=100, content_type="application/pdf")
    assert safe is not None
    assert safe["rejected"] is False
    assert "data" not in safe
    unsafe = attachment_meta_safe(filename="../evil.exe", size=10, content_type="application/x-msdownload")
    assert unsafe is not None
    assert unsafe["rejected"] is True
    assert sanitize_attachment_filename("../../etc/passwd") == "passwd"
    inbound = normalize_inbound(
        workspace_id="ws",
        from_address="a@b.com",
        text_body="hi",
        attachments_meta=[
            {"filename": "ok.txt", "size": 3, "content_type": "text/plain", "data": "SECRET"},
            {"filename": "bad.bat", "size": 9, "content_type": "application/x-bat"},
        ],
    )
    assert all("data" not in a for a in inbound["attachments_meta"])
    assert any(a.get("rejected") for a in inbound["attachments_meta"])


def test_cursor_advances(outreach: OutreachService) -> None:
    seeded = _seed_sent(outreach)
    account = {
        "id": "acct-1",
        "email_address": "sender@keprix.test",
        "username": "sender@keprix.test",
    }
    messages = [
        {
            "message_id": "scan-1@mail",
            "uid": 42,
            "folder": "INBOX",
            "from_address": "ada@example.com",
            "to_addresses": ["sender@keprix.test"],
            "subject": "Re: Hello",
            "body_text": "interested",
            "in_reply_to": seeded["message"]["provider_message_id"],
            "references": [],
            "received_at": datetime.now(timezone.utc),
            "attachments_meta": [],
        }
    ]
    out = outreach.scan_replies("ws_1", messages=messages, account=account)
    assert out["scanned"] == 1
    assert out["matched"] == 1
    cursor = outreach.store.get_inbound_cursor(
        "ws_1", account_id="acct-1", mailbox="sender@keprix.test", cursor_kind="imap_uid"
    )
    assert cursor is not None
    assert cursor["cursor_value"] == "42"

    # Idempotent re-scan same Message-ID
    out2 = outreach.scan_replies("ws_1", messages=messages, account=account)
    assert out2["deduped"] == 1
