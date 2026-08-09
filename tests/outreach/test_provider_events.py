"""Provider event normalization / apply tests (Prompt 625)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.provider_events import (
    apply_provider_event,
    normalize_mailgun_events,
    normalize_sendgrid_events,
    normalize_ses_events,
    verify_mailgun_signature,
)
from keprix.outreach.reconcile import reconcile_delivery
from keprix.outreach.service import OutreachService
from keprix.outreach.store import reset_outreach_store_for_tests


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


@pytest.fixture()
def outreach(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> OutreachService:
    path = tmp_path / "outreach.sqlite"
    store = reset_outreach_store_for_tests(path)
    reset_outreach_ops_store_for_tests(path)
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "1")

    class _Crm:
        entries: list[dict] = []

        def is_kill_switch_on(self, *a, **k):
            return False

        def is_suppressed(self, ws, channel="email", address=""):
            return any(
                e.get("address") == str(address).lower() and e.get("channel") == channel
                for e in self.entries
            )

        def create_suppression_entry(self, ws, **fields):
            row = {"workspace_id": ws, **fields, "address": str(fields.get("address") or "").lower()}
            self.entries.append(row)
            return row

    crm = _Crm()
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: crm)
    svc = OutreachService(store=store)
    svc._test_crm = crm  # type: ignore[attr-defined]
    return svc


def _seed_sent_message(outreach: OutreachService, *, email: str = "lead@example.com") -> dict:
    campaign = outreach.create_campaign("ws_1", "c", status="active", business_hours_only=False)
    sequence = outreach.create_sequence(
        "ws_1", "s", steps=[{"subject": "S", "body": "B", "delay_hours": 24}]
    )
    lead = outreach.add_leads(
        "ws_1", campaign_id=campaign["id"], leads=[{"email": email, "first_name": "L"}]
    )["leads"][0]
    enr = outreach.enroll_lead("ws_1", lead["id"], sequence["id"])["enrollment"]
    now = _iso(datetime.now(timezone.utc))
    msg = outreach.store.create_message(
        enrollment_id=enr["id"],
        workspace_id="ws_1",
        channel="email",
        subject="S",
        body="B",
        sent_at=now,
        provider="sendgrid",
        provider_message_id="pmid-1",
        delivery_state="sent",
        step_order=1,
        idempotency_key=f"enrollment:{enr['id']}:step:1",
    )
    return {"campaign": campaign, "sequence": sequence, "lead": lead, "enrollment": enr, "message": msg}


def test_normalize_fixtures_delivered_bounce_complaint() -> None:
    sg = normalize_sendgrid_events(
        [
            {"event": "delivered", "sg_message_id": "pmid-1.recvd", "sg_event_id": "e1", "email": "a@b.c"},
            {
                "event": "bounce",
                "type": "bounce",
                "sg_message_id": "pmid-2",
                "sg_event_id": "e2",
                "email": "a@b.c",
            },
            {"event": "spamreport", "sg_message_id": "pmid-3", "sg_event_id": "e3", "email": "a@b.c"},
        ]
    )
    assert [e["event_type"] for e in sg] == ["delivered", "hard_bounce", "complaint"]

    mg = normalize_mailgun_events(
        {
            "event-data": {
                "event": "delivered",
                "id": "mg1",
                "recipient": "a@b.c",
                "message": {"headers": {"message-id": "<pmid-mg>"}},
            }
        }
    )
    assert mg[0]["event_type"] == "delivered"

    ses = normalize_ses_events(
        {
            "notificationType": "Bounce",
            "bounce": {
                "bounceType": "Permanent",
                "bouncedRecipients": [{"emailAddress": "a@b.c"}],
            },
            "mail": {"messageId": "ses-1", "destination": ["a@b.c"]},
        }
    )
    assert ses[0]["event_type"] == "hard_bounce"


def test_hard_bounce_creates_suppression_and_stops(outreach: OutreachService) -> None:
    seeded = _seed_sent_message(outreach, email="bounce@example.com")
    events = normalize_sendgrid_events(
        [
            {
                "event": "bounce",
                "type": "bounce",
                "sg_message_id": "pmid-1",
                "sg_event_id": "bounce-1",
                "email": "bounce@example.com",
            }
        ]
    )
    result = apply_provider_event("ws_1", events[0], store=outreach.store)
    assert result["ok"] is True
    assert any(e["address"] == "bounce@example.com" for e in outreach._test_crm.entries)  # type: ignore[attr-defined]
    msg = outreach.store.get_message("ws_1", seeded["message"]["id"])
    assert msg and msg.get("delivery_state") == "hard_bounce"
    assert msg.get("bounced") in (1, True)
    enr = outreach.store.get_enrollment(seeded["enrollment"]["id"])
    assert enr and enr["status"] == "stopped_suppressed"


def test_duplicate_idempotency_ignored(outreach: OutreachService) -> None:
    _seed_sent_message(outreach)
    events = normalize_sendgrid_events(
        [
            {
                "event": "delivered",
                "sg_message_id": "pmid-1",
                "sg_event_id": "dup-1",
                "email": "lead@example.com",
            }
        ]
    )
    r1 = apply_provider_event("ws_1", events[0], store=outreach.store)
    r2 = apply_provider_event("ws_1", events[0], store=outreach.store)
    assert r1["ok"] is True
    assert r2.get("duplicate") is True


def test_invalid_signature_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAILGUN_WEBHOOK_SIGNING_KEY", "test-secret")
    assert (
        verify_mailgun_signature(timestamp="1", token="t", signature="bad", signing_key="test-secret")
        is False
    )
    # Correct signature
    import hashlib
    import hmac

    sig = hmac.new(b"test-secret", b"1t", hashlib.sha256).hexdigest()
    assert verify_mailgun_signature(timestamp="1", token="t", signature=sig) is True


def test_monotonic_delivered_then_bounce(outreach: OutreachService) -> None:
    seeded = _seed_sent_message(outreach)
    mid = seeded["message"]["id"]
    delivered = normalize_sendgrid_events(
        [{"event": "delivered", "sg_message_id": "pmid-1", "sg_event_id": "d1", "email": "lead@example.com"}]
    )[0]
    apply_provider_event("ws_1", delivered, store=outreach.store)
    msg = outreach.store.get_message("ws_1", mid)
    assert msg and msg["delivery_state"] == "delivered"
    bounce = normalize_sendgrid_events(
        [
            {
                "event": "bounce",
                "type": "bounce",
                "sg_message_id": "pmid-1",
                "sg_event_id": "b1",
                "email": "lead@example.com",
            }
        ]
    )[0]
    apply_provider_event("ws_1", bounce, store=outreach.store)
    msg2 = outreach.store.get_message("ws_1", mid)
    assert msg2 and msg2["delivery_state"] == "hard_bounce"


def test_opened_ignored_when_tracking_disabled(outreach: OutreachService) -> None:
    from keprix.outreach.ops import get_outreach_ops_store

    seeded = _seed_sent_message(outreach)
    get_outreach_ops_store().set_control(
        "ws_1",
        paused=False,
        settings={"allow_open_tracking": False, "allow_click_tracking": False},
    )
    opened = normalize_sendgrid_events(
        [{"event": "open", "sg_message_id": "pmid-1", "sg_event_id": "o1", "email": "lead@example.com"}]
    )[0]
    result = apply_provider_event("ws_1", opened, store=outreach.store)
    assert result.get("ignored") is True
    msg = outreach.store.get_message("ws_1", seeded["message"]["id"])
    assert not msg.get("opened_at")


def test_reconcile_flags_stuck_sends(outreach: OutreachService) -> None:
    seeded = _seed_sent_message(outreach)
    old = _iso(datetime.now(timezone.utc) - timedelta(hours=2))
    outreach.store.update_message("ws_1", seeded["message"]["id"], sent_at=old, delivery_state="sent")
    out = reconcile_delivery(workspace_id="ws_1", older_than_minutes=30, store=outreach.store)
    assert out["drift_count"] >= 1
    assert seeded["message"]["id"] in out["drift_message_ids"]
    msg = outreach.store.get_message("ws_1", seeded["message"]["id"])
    assert msg and "delivery_drift" in str(msg.get("send_error") or "")
