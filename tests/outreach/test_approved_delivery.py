"""Approved outreach delivery tests (Prompt 625)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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
    for key in (
        "SENDGRID_API_KEY",
        "MAILGUN_API_KEY",
        "MAILGUN_DOMAIN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SES_REGION",
    ):
        monkeypatch.delenv(key, raising=False)

    class _Crm:
        suppressed: set[str] = set()

        def is_kill_switch_on(self, *a, **k):
            return False

        def is_suppressed(self, ws, channel="email", address=""):
            return str(address or "").lower() in self.suppressed

        def create_suppression_entry(self, *a, **k):
            return {}

    crm = _Crm()
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: crm)
    monkeypatch.setattr(
        "keprix.crm.nurture.cadence_allows_send",
        lambda *a, **k: (True, None),
    )
    svc = OutreachService(store=store)
    svc._test_crm = crm  # type: ignore[attr-defined]
    return svc


def _seed(outreach: OutreachService, *, email: str = "ada@example.com") -> dict:
    campaign = outreach.create_campaign(
        "ws_1",
        "Deliv camp",
        status="active",
        business_hours_only=False,
        require_approval=True,
    )
    sequence = outreach.create_sequence(
        "ws_1",
        "seq",
        steps=[{"subject": "Hello {{first_name}}", "body": "Hi {{first_name}}", "delay_hours": 24}],
    )
    added = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[{"email": email, "first_name": "Ada", "company": "Analytical"}],
    )
    lead = added["leads"][0]
    enrolled = outreach.enroll_lead("ws_1", lead["id"], sequence["id"])
    return {
        "campaign": campaign,
        "sequence": sequence,
        "lead": lead,
        "enrollment": enrolled["enrollment"],
    }


def test_dry_run_success_stamps_without_account(
    outreach: OutreachService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="d1")
    assert result["items"][0]["action"] == "soft_wall_queued"
    approval_id = result["items"][0]["approval_id"]
    message_id = result["items"][0]["message_id"]

    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=True)
    assert approved["ok"] is True
    assert approved["send"].get("dry_run") is True
    msg = outreach.store.get_message("ws_1", message_id)
    assert msg and msg.get("sent_at")
    assert msg.get("provider") == "dry_run"
    assert msg.get("provider_message_id")
    enr = outreach.store.get_enrollment(eid)
    assert enr and int(enr["current_step"] or 0) == 1


def test_not_configured_no_sent_at_no_step_advance(
    outreach: OutreachService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="nc")
    approval_id = result["items"][0]["approval_id"]
    message_id = result["items"][0]["message_id"]

    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=False)
    assert approved["ok"] is False
    assert approved["reason"] == "not_configured"
    msg = outreach.store.get_message("ws_1", message_id)
    assert msg and not msg.get("sent_at")
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "awaiting_approval"
    assert int(enr["current_step"] or 0) == 0


def test_soft_wall_approve_mocked_smtp(
    outreach: OutreachService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="smtp")
    approval_id = result["items"][0]["approval_id"]
    message_id = result["items"][0]["message_id"]

    account = {
        "id": "acct_1",
        "email_address": "sender@example.com",
        "username": "sender@example.com",
        "smtp_host": "localhost",
        "smtp_port": 587,
        "use_starttls": True,
        "password": "secret",
    }

    def fake_smtp(acct, **kwargs):
        return {"message_id": "smtp-msg-123", "provider_message_id": "smtp-msg-123"}

    monkeypatch.setattr("keprix.email.helpers.send_smtp_message", fake_smtp)
    monkeypatch.setattr(
        "keprix.outreach.delivery.resolve_sender",
        lambda *a, **k: {
            "mode": "smtp",
            "provider": "smtp",
            "account_id": "acct_1",
            "mailbox": "sender@example.com",
            "account": account,
        },
    )

    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=False)
    assert approved["ok"] is True
    assert approved["send"].get("provider_message_id") == "smtp-msg-123"
    msg = outreach.store.get_message("ws_1", message_id)
    assert msg and msg.get("sent_at")
    assert msg.get("provider_message_id") == "smtp-msg-123"
    assert msg.get("provider") == "smtp"
    enr = outreach.store.get_enrollment(eid)
    assert enr and int(enr["current_step"] or 0) == 1


def test_idempotent_resend_same_key(
    outreach: OutreachService, monkeypatch: pytest.MonkeyPatch
) -> None:
    from keprix.outreach.delivery import send_approved_message

    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "1")
    first = send_approved_message(
        workspace_id="ws_1",
        to_email="a@example.com",
        subject="S",
        body="B",
        idempotency_key="k1",
        dry_run=True,
    )
    existing = {
        "id": "m1",
        "sent_at": _iso(datetime.now(timezone.utc)),
        "provider": "dry_run",
        "provider_message_id": first["provider_message_id"],
        "delivery_state": "sent",
        "idempotency_key": "k1",
    }
    second = send_approved_message(
        workspace_id="ws_1",
        to_email="a@example.com",
        subject="S",
        body="B",
        idempotency_key="k1",
        dry_run=True,
        existing_message=existing,
    )
    assert second.get("idempotent") is True
    assert second.get("provider_message_id") == first["provider_message_id"]


def test_suppression_blocks_send_on_revalidation(
    outreach: OutreachService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach, email="block@example.com")
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="sup")
    approval_id = result["items"][0]["approval_id"]
    outreach._test_crm.suppressed.add("block@example.com")  # type: ignore[attr-defined]
    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=True)
    assert approved["ok"] is False
    assert approved["reason"] == "crm_suppressed"
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "stopped_suppressed"
    assert int(enr["current_step"] or 0) == 0
