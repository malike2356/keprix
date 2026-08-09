"""Durable sequence scheduler tests (Prompt 624)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.scheduler import next_open_business_window, run_scheduler_tick
from keprix.outreach.service import OutreachService
from keprix.outreach.store import OutreachStore, reset_outreach_store_for_tests


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

        def is_kill_switch_on(self, *a, **k):
            return False

        def is_suppressed(self, ws, channel="email", address=""):
            return str(address or "").lower() in self.suppressed

    crm = _Crm()
    monkeypatch.setattr("keprix.crm.store.get_crm_store", lambda: crm)
    monkeypatch.setattr(
        "keprix.crm.nurture.cadence_allows_send",
        lambda *a, **k: (True, None),
    )
    svc = OutreachService(store=store)
    svc._test_crm = crm  # type: ignore[attr-defined]
    return svc


def _seed(
    outreach: OutreachService,
    *,
    business_hours_only: bool = False,
    daily_cap: int = 50,
    require_approval: bool = False,
    timezone_name: str = "Europe/London",
    email: str = "ada@example.com",
) -> dict:
    campaign = outreach.create_campaign(
        "ws_1",
        "Sched camp",
        status="active",
        business_hours_only=business_hours_only,
        daily_cap=daily_cap,
        require_approval=require_approval,
        timezone=timezone_name,
    )
    sequence = outreach.create_sequence(
        "ws_1",
        "seq",
        steps=[
            {"subject": "S1", "body": "Step 1", "delay_hours": 24},
            {"subject": "S2", "body": "Step 2", "delay_hours": 24},
        ],
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


def test_concurrent_claim_one_wins(outreach: OutreachService) -> None:
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = _iso(datetime.now(timezone.utc))
    store = outreach.store

    def claim(worker: str):
        return store.claim_due_enrollments(
            now_iso=now, limit=10, worker_id=worker, lease_seconds=60, workspace_id="ws_1"
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(claim, "w1")
        f2 = pool.submit(claim, "w2")
        r1, r2 = f1.result(), f2.result()
    ids = [r["id"] for r in r1] + [r["id"] for r in r2]
    assert ids.count(eid) == 1
    assert len(r1) + len(r2) == 1


def test_stale_lease_reclaim(outreach: OutreachService) -> None:
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    past = _iso(datetime.now(timezone.utc) - timedelta(minutes=5))
    outreach.store.update_enrollment(
        eid, locked_until=past, locked_by="dead-worker", last_claimed_at=past
    )
    now = _iso(datetime.now(timezone.utc))
    claimed = outreach.store.claim_due_enrollments(
        now_iso=now, limit=5, worker_id="alive", lease_seconds=60, workspace_id="ws_1"
    )
    assert len(claimed) == 1
    assert claimed[0]["id"] == eid
    assert claimed[0]["locked_by"] == "alive"


def test_idempotent_message_key(outreach: OutreachService) -> None:
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    r1 = outreach.process_due("ws_1", dry_run=True, now=now, worker_id="w1")
    assert r1["processed"] == 1
    mid = r1["items"][0]["message_id"]
    # Force same step due again (crash-like re-queue without advance would keep step;
    # here re-create by resetting step and due)
    outreach.store.update_enrollment(
        eid, current_step=0, status="active", next_run_at=_iso(now - timedelta(minutes=1))
    )
    r2 = outreach.process_due("ws_1", dry_run=True, now=now, worker_id="w2")
    assert r2["processed"] == 1
    assert r2["items"][0]["message_id"] == mid
    count = outreach.store.count_messages_for_enrollment_step(eid, 1)
    assert count == 1


def test_soft_wall_park_approve_reject(outreach: OutreachService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach, require_approval=True)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="sw")
    assert result["processed"] == 1
    assert result["items"][0]["action"] == "soft_wall_queued"
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "awaiting_approval"
    assert int(enr["current_step"] or 0) == 0
    assert enr.get("next_run_at") in (None, "")
    approval_id = result["items"][0]["approval_id"]

    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=True)
    assert approved["ok"] is True
    enr2 = outreach.store.get_enrollment(eid)
    assert enr2 and int(enr2["current_step"] or 0) == 1
    assert enr2["status"] == "active"

    # Second step Soft Wall then reject
    outreach.store.update_enrollment(eid, next_run_at=_iso(now - timedelta(minutes=1)))
    r2 = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="sw2")
    assert r2["items"][0]["action"] == "soft_wall_queued"
    rej_id = r2["items"][0]["approval_id"]
    rejected = outreach.reject_soft_wall("ws_1", rej_id)
    assert rejected["ok"] is True
    enr3 = outreach.store.get_enrollment(eid)
    assert enr3 and enr3["status"] == "cancelled"
    assert int(enr3["current_step"] or 0) == 1  # not advanced on reject


def test_crash_simulation_still_claimable(outreach: OutreachService) -> None:
    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    claimed = outreach.store.claim_due_enrollments(
        now_iso=_iso(now),
        limit=1,
        worker_id="crasher",
        lease_seconds=30,
        workspace_id="ws_1",
    )
    assert len(claimed) == 1
    step_before = int(claimed[0]["current_step"] or 0)
    # Simulate crash: leave lock, no advance
    future = _iso(now + timedelta(seconds=1))
    # Expire lease
    outreach.store.update_enrollment(eid, locked_until=_iso(now - timedelta(seconds=1)))
    again = outreach.store.claim_due_enrollments(
        now_iso=future, limit=1, worker_id="recover", lease_seconds=30, workspace_id="ws_1"
    )
    assert len(again) == 1
    assert int(again[0]["current_step"] or 0) == step_before


def test_retry_backoff_and_dead_letter(outreach: OutreachService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    monkeypatch.setenv("KEPRIX_OUTREACH_SOFT_WALL", "0")
    seeded = _seed(outreach, require_approval=False)
    eid = seeded["enrollment"]["id"]

    def fail_send(**kwargs):
        return {"sent": False, "error": "smtp_temp", "to": kwargs.get("to_email")}

    monkeypatch.setattr(outreach, "_send_message", fail_send)
    now = datetime.now(timezone.utc)
    r1 = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="r1", max_attempts=3)
    assert r1["items"][0]["action"] == "retry_backoff"
    enr = outreach.store.get_enrollment(eid)
    assert enr and int(enr["attempt_count"] or 0) == 1
    assert enr["status"] == "active"
    assert enr.get("next_run_at")

    for i in range(2):
        outreach.store.update_enrollment(eid, next_run_at=_iso(now - timedelta(minutes=1)))
        outreach.process_due(
            "ws_1", dry_run=False, now=now + timedelta(seconds=i + 1), worker_id=f"r{i+2}", max_attempts=3
        )
    enr2 = outreach.store.get_enrollment(eid)
    assert enr2 and enr2["status"] == "dead_letter"
    assert enr2.get("dead_letter_at")
    retried = outreach.store.retry_dead_letter(eid)
    assert retried and retried["status"] == "active"


def test_business_hours_friday_evening_to_monday(outreach: OutreachService) -> None:
    seeded = _seed(outreach, business_hours_only=True, timezone_name="Europe/London")
    eid = seeded["enrollment"]["id"]
    # Friday 18:00 London
    friday = datetime(2026, 8, 7, 17, 0, tzinfo=timezone.utc)  # 18:00 BST
    local = friday.astimezone(ZoneInfo("Europe/London"))
    assert local.weekday() == 4
    assert local.hour >= 17
    outreach.store.update_enrollment(eid, next_run_at=_iso(friday - timedelta(minutes=1)))
    result = outreach.process_due("ws_1", dry_run=True, now=friday, worker_id="bh")
    assert result["processed"] == 0
    assert any(s["reason"] == "outside_business_hours" for s in result["skipped_items"])
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["next_run_at"]
    nxt = datetime.fromisoformat(enr["next_run_at"])
    local_nxt = nxt.astimezone(ZoneInfo("Europe/London"))
    assert local_nxt.weekday() == 0  # Monday
    assert local_nxt.hour == 9
    expected = next_open_business_window("Europe/London", friday)
    assert abs((nxt - expected).total_seconds()) < 2


def test_daily_cap_defers_to_midnight(outreach: OutreachService) -> None:
    seeded = _seed(outreach, daily_cap=1, business_hours_only=False)
    eid = seeded["enrollment"]["id"]
    campaign_id = seeded["campaign"]["id"]
    now = datetime.now(timezone.utc)
    # Consume the daily cap with a sent message on another enrollment path
    other = outreach.add_leads(
        "ws_1",
        campaign_id=campaign_id,
        leads=[{"email": "other@example.com"}],
    )["leads"][0]
    enr2 = outreach.enroll_lead("ws_1", other["id"], seeded["sequence"]["id"])["enrollment"]
    outreach.store.create_message(
        enrollment_id=enr2["id"],
        channel="email",
        body="cap",
        sent_at=_iso(now),
        step_order=1,
        idempotency_key=f"enrollment:{enr2['id']}:step:1",
    )
    outreach.store.update_enrollment(enr2["id"], status="completed", next_run_at=None)
    outreach.store.update_enrollment(eid, next_run_at=_iso(now - timedelta(minutes=1)))
    result = outreach.process_due("ws_1", dry_run=True, now=now, worker_id="cap")
    assert any(s["reason"] == "daily_cap" for s in result["skipped_items"])
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "active"
    assert int(enr["current_step"] or 0) == 0
    assert enr.get("next_run_at")
    # Deferred into the future (next midnight), not left hot-due
    assert enr["next_run_at"] > _iso(now)


def test_workspace_pause_skips_without_consuming_step(outreach: OutreachService) -> None:
    from keprix.outreach.ops import get_outreach_ops_store

    seeded = _seed(outreach)
    eid = seeded["enrollment"]["id"]
    get_outreach_ops_store().set_control("ws_1", paused=True, reason="test")
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=True, now=now, worker_id="pause")
    assert result["processed"] == 0
    assert any(s["reason"] == "outreach_paused" for s in result["skipped_items"])
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "active"
    assert int(enr["current_step"] or 0) == 0


def test_suppression_stops(outreach: OutreachService) -> None:
    seeded = _seed(outreach, email="stopme@example.com")
    eid = seeded["enrollment"]["id"]
    outreach._test_crm.suppressed.add("stopme@example.com")  # type: ignore[attr-defined]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=True, now=now, worker_id="supp")
    assert any(s["reason"] == "crm_suppressed" for s in result["skipped_items"])
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "stopped_suppressed"
    assert int(enr["current_step"] or 0) == 0


def test_delayed_approval_revalidation_suppress(outreach: OutreachService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_OUTREACH_DRY_RUN", "0")
    seeded = _seed(outreach, require_approval=True, email="race@example.com")
    eid = seeded["enrollment"]["id"]
    now = datetime.now(timezone.utc)
    result = outreach.process_due("ws_1", dry_run=False, now=now, worker_id="race")
    approval_id = result["items"][0]["approval_id"]
    assert outreach.store.get_enrollment(eid)["status"] == "awaiting_approval"
    # Suppress between queue and approve
    outreach._test_crm.suppressed.add("race@example.com")  # type: ignore[attr-defined]
    approved = outreach.approve_soft_wall("ws_1", approval_id, dry_run=True)
    assert approved["ok"] is False
    assert approved["reason"] == "crm_suppressed"
    enr = outreach.store.get_enrollment(eid)
    assert enr and enr["status"] == "stopped_suppressed"
    assert int(enr["current_step"] or 0) == 0


def test_run_scheduler_tick_wrapper(outreach: OutreachService) -> None:
    _seed(outreach)
    out = run_scheduler_tick("ws_1", dry_run=True, service=outreach, worker_id="cli")
    assert "processed" in out
    health = outreach.get_scheduler_health("ws_1")
    assert "queue_depth" in health
