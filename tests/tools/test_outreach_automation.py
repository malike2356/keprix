"""Tests for K02 outreach automation on Keprix."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from keprix.outreach.classify import classify_reply_heuristic
from keprix.outreach.cron_seed import OUTREACH_CRON_JOBS
from keprix.outreach.service import OutreachService
from keprix.outreach.store import OutreachStore, reset_outreach_store_for_tests


@pytest.fixture()
def outreach(tmp_path: Path) -> OutreachService:
    store = reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    return OutreachService(store=store)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def test_campaign_crud_and_stats(outreach: OutreachService) -> None:
    campaign = outreach.create_campaign(
        "ws_1",
        "Q3 outbound",
        status="active",
        business_hours_only=False,
        daily_cap=100,
        default_booking_link="https://cal.example/book",
    )
    assert campaign["name"] == "Q3 outbound"
    assert campaign["status"] == "active"

    updated = outreach.update_campaign("ws_1", campaign["id"], status="paused")
    assert updated and updated["status"] == "paused"

    outreach.update_campaign("ws_1", campaign["id"], status="active")
    stats = outreach.get_campaign_stats("ws_1", campaign["id"])
    assert stats["leads"] == 0
    assert stats["campaign"]["id"] == campaign["id"]


def test_sequence_with_three_steps_executes_on_schedule(outreach: OutreachService) -> None:
    campaign = outreach.create_campaign(
        "ws_1",
        "Seq camp",
        status="active",
        business_hours_only=False,
    )
    sequence = outreach.create_sequence(
        "ws_1",
        "3-step nurture",
        steps=[
            {"subject": "Hi {{first_name}}", "body": "Step 1 for {{company}}", "delay_hours": 0},
            {"subject": "Follow up", "body": "Step 2", "delay_hours": 0},
            {"subject": "Last touch", "body": "Step 3 {{booking_link}}", "delay_hours": 24},
        ],
    )
    assert len(sequence["steps"]) == 3

    added = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[{"email": "ada@example.com", "first_name": "Ada", "company": "Analytical"}],
    )
    lead = added["leads"][0]
    enrolled = outreach.enroll_lead("ws_1", lead["id"], sequence["id"])
    assert enrolled["enrollment"]["status"] == "active"

    now = datetime.now(timezone.utc)
    r1 = outreach.process_due("ws_1", dry_run=True, now=now)
    assert r1["processed"] == 1
    assert r1["items"][0]["action"] in ("sent_step", "sent_final")

    # Force next step due immediately
    enroll_id = enrolled["enrollment"]["id"]
    outreach.store.update_enrollment(enroll_id, next_run_at=_iso(now - timedelta(minutes=1)))
    r2 = outreach.process_due("ws_1", dry_run=True, now=now)
    assert r2["processed"] == 1

    outreach.store.update_enrollment(enroll_id, next_run_at=_iso(now - timedelta(minutes=1)))
    r3 = outreach.process_due("ws_1", dry_run=True, now=now)
    assert r3["processed"] == 1
    assert r3["items"][0]["action"] == "sent_final"

    final = outreach.store.get_enrollment(enroll_id)
    assert final and final["status"] == "completed"

    lead_after = outreach.store.get_lead("ws_1", lead["id"])
    assert lead_after and lead_after["status"] == "contacted"


def test_pipeline_move_and_board(outreach: OutreachService) -> None:
    campaign = outreach.create_campaign("ws_1", "Pipe", status="active", business_hours_only=False)
    added = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[
            {"email": "a@x.com", "first_name": "A"},
            {"email": "b@x.com", "first_name": "B"},
        ],
    )
    outreach.move_lead("ws_1", added["leads"][0]["id"], "interested")
    outreach.move_lead("ws_1", added["leads"][1]["id"], "booking")
    board = outreach.get_pipeline("ws_1", campaign["id"])
    assert board["stages"]["interested"] == 1
    assert board["stages"]["booking"] == 1
    assert board["total"] == 2


def test_reply_classification_booking_objection_unsubscribe(outreach: OutreachService) -> None:
    assert classify_reply_heuristic("", "Please unsubscribe me")["classification"] == "unsubscribe"
    assert (
        classify_reply_heuristic("Re: intro", "Happy to book a call next week")["classification"]
        == "booking_intent"
    )
    assert (
        classify_reply_heuristic("", "Too expensive for us right now")["classification"] == "objection"
    )

    campaign = outreach.create_campaign(
        "ws_1",
        "Reply camp",
        status="active",
        business_hours_only=False,
        default_booking_link="https://cal.example/x",
    )
    sequence = outreach.create_sequence(
        "ws_1",
        "seq",
        steps=[
            {"body": "hello", "delay_hours": 24},
            {"body": "hello2", "delay_hours": 24},
        ],
    )
    added = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[{"email": "ceo@acme.com", "first_name": "Pat"}],
    )
    lead = added["leads"][0]
    outreach.enroll_lead("ws_1", lead["id"], sequence["id"])

    booking = outreach.classify_and_apply_reply(
        "ws_1",
        from_address="ceo@acme.com",
        subject="Re",
        body="Let's schedule a meeting this week",
    )
    assert booking["classification"]["classification"] == "booking_intent"
    assert booking["lead"]["status"] == "booking"
    assert booking["stopped_enrollments"]
    assert booking["draft_response"] and "https://cal.example/x" in booking["draft_response"]

    # Fresh lead for unsubscribe
    added2 = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[{"email": "out@acme.com"}],
    )
    lead2 = added2["leads"][0]
    outreach.enroll_lead("ws_1", lead2["id"], sequence["id"])
    unsub = outreach.classify_and_apply_reply(
        "ws_1",
        from_address="out@acme.com",
        body="Please unsubscribe / remove me",
    )
    assert unsub["classification"]["classification"] == "unsubscribe"
    assert unsub["lead"]["status"] == "unsubscribed"

    # Objection draft
    added3 = outreach.add_leads(
        "ws_1",
        campaign_id=campaign["id"],
        leads=[{"email": "obj@acme.com"}],
    )
    lead3 = added3["leads"][0]
    obj = outreach.classify_and_apply_reply(
        "ws_1",
        from_address="obj@acme.com",
        body="Too expensive and we already have a vendor",
    )
    assert obj["classification"]["classification"] == "objection"
    assert obj["draft_response"]


def test_csv_import_and_daily_digest(outreach: OutreachService) -> None:
    campaign = outreach.create_campaign("ws_1", "CSV", status="active", business_hours_only=False)
    csv_text = "email,first_name,company\none@x.com,One,Acme\ntwo@x.com,Two,Beta\n"
    result = outreach.add_leads("ws_1", campaign_id=campaign["id"], csv_text=csv_text)
    assert result["created"] == 2
    digest = outreach.daily_digest("ws_1")
    assert digest["new_leads"] >= 2
    assert "Outreach digest" in digest["message"]


def test_tools_registered_and_dispatchable(tmp_path: Path) -> None:
    reset_outreach_store_for_tests(tmp_path / "tools.sqlite")
    import tools.outreach_tools as outreach_tools  # noqa: F401
    from tools.registry import registry

    assert registry.get_entry("outreach_create_campaign") is not None
    raw = registry.dispatch(
        "outreach_create_campaign",
        {"workspace_id": "ws_t", "name": "Tool Camp", "status": "active", "business_hours_only": False},
    )
    data = json.loads(raw)
    assert data["campaign"]["name"] == "Tool Camp"

    seq = json.loads(
        registry.dispatch(
            "outreach_create_sequence",
            {
                "workspace_id": "ws_t",
                "name": "s",
                "steps": [
                    {"body": "1", "delay_hours": 0},
                    {"body": "2", "delay_hours": 0},
                    {"body": "3", "delay_hours": 0},
                ],
            },
        )
    )
    assert len(seq["sequence"]["steps"]) == 3


def test_cron_job_specs_defined() -> None:
    names = {j["name"] for j in OUTREACH_CRON_JOBS}
    assert names == {"outreach-process-due", "outreach-scan-replies", "outreach-daily-digest"}
    schedules = {j["name"]: j["schedule"] for j in OUTREACH_CRON_JOBS}
    assert schedules["outreach-process-due"] == "every 5m"
    assert schedules["outreach-scan-replies"] == "every 2m"
    assert schedules["outreach-daily-digest"] == "0 8 * * *"
