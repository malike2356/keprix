"""Integration-style tests for status page outage → notify → resolve."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from keprix.status_page import (
    FAILURE_THRESHOLD,
    RECOVERY_MS,
    MaintenanceConflictError,
    MaintenanceLeadTimeError,
    NotificationLog,
    StatusStore,
    notify_active_users,
    run_health_cycle,
    schedule_maintenance,
)


def test_outage_creates_incident_and_resolves():
    store = StatusStore(
        product="keprix",
        endpoints=[{"id": "api", "name": "API", "url": "https://example.test/health"}],
    )
    fail = {"ok": False, "error": "down"}

    def ping_fn(_ep):
        return fail

    created = None
    for i in range(FAILURE_THRESHOLD):
        now = datetime(2026, 8, 10, 12, i, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        result = run_health_cycle(store, ping_fn=ping_fn, now=now)
        created = result["created"]
    assert created is not None
    assert created["autoCreated"] is True
    log = NotificationLog()
    notify_active_users(created, ["a@example.com"], log=log)
    assert len(log.records) == 1

    def ok_fn(_ep):
        return {"ok": True, "statusCode": 200}

    t0 = datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc)
    run_health_cycle(store, ping_fn=ok_fn, now=t0.isoformat().replace("+00:00", "Z"), recovery_ms=RECOVERY_MS)
    mid = run_health_cycle(
        store,
        ping_fn=ok_fn,
        now=(t0 + timedelta(minutes=2)).isoformat().replace("+00:00", "Z"),
        recovery_ms=RECOVERY_MS,
    )
    assert mid["resolved"] == []
    done = run_health_cycle(
        store,
        ping_fn=ok_fn,
        now=(t0 + timedelta(milliseconds=RECOVERY_MS)).isoformat().replace("+00:00", "Z"),
        recovery_ms=RECOVERY_MS,
    )
    assert done["resolved"]
    assert store.get_incident(created["id"])["phase"] == "resolved"
    snap = store.snapshot()
    assert "uptime90d" in snap
    assert snap["overall"] in ("operational", "degraded", "outage", "maintenance")


def test_maintenance_rules():
    store = StatusStore(product="keprix", endpoints=[])
    now = "2026-08-10T00:00:00.000Z"
    schedule_maintenance(
        store,
        title="Window A",
        description="desc",
        affected_services=["api"],
        starts_at="2026-08-13T02:00:00.000Z",
        ends_at="2026-08-13T04:00:00.000Z",
        now=now,
    )
    try:
        schedule_maintenance(
            store,
            title="Overlap",
            description="x",
            affected_services=["api"],
            starts_at="2026-08-13T03:00:00.000Z",
            ends_at="2026-08-13T05:00:00.000Z",
            now=now,
        )
        assert False, "expected conflict"
    except MaintenanceConflictError:
        pass
    try:
        schedule_maintenance(
            store,
            title="Soon",
            description="x",
            affected_services=["api"],
            starts_at="2026-08-10T12:00:00.000Z",
            ends_at="2026-08-10T13:00:00.000Z",
            now=now,
        )
        assert False, "expected lead time"
    except MaintenanceLeadTimeError:
        pass
