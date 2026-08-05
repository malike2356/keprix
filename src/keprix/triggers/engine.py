"""Trigger engine: schedule tick, event enqueue, leased worker."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.triggers.dispatcher import dispatch_action
from keprix.triggers.schedule import compute_next_run, iso_utc
from keprix.triggers.store import TriggerStore, get_trigger_store

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def tick_schedules(store: TriggerStore | None = None) -> list[dict[str, Any]]:
    """Enqueue one run per due schedule trigger and advance next_run_at."""
    store = store or get_trigger_store()
    now = _utcnow()
    queued: list[dict[str, Any]] = []
    for trigger in store.due_schedule_triggers(now_iso=now.isoformat()):
        run = store.enqueue_run(trigger, payload={"scheduled_for": trigger.next_run_at})
        trigger.last_run_at = now.isoformat()
        if trigger.schedule:
            nxt = compute_next_run(trigger.schedule, timezone_name=trigger.timezone, from_dt=now)
            trigger.next_run_at = iso_utc(nxt)
            # once schedules disable after fire
            if trigger.schedule.type == "once":
                trigger.enabled = False
                trigger.next_run_at = None
        store.update_trigger(trigger)
        queued.append({"trigger_id": trigger.id, "run_id": run.id})
    return queued


def enqueue_event(
    *,
    source: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    workspace_id: str | None = None,
    store: TriggerStore | None = None,
) -> list[dict[str, Any]]:
    store = store or get_trigger_store()
    queued: list[dict[str, Any]] = []
    for trigger in store.list_event_triggers(source=source, event_type=event_type, workspace_id=workspace_id):
        run = store.enqueue_run(
            trigger,
            payload={"source": source, "event_type": event_type, **(payload or {})},
        )
        queued.append({"trigger_id": trigger.id, "run_id": run.id})
    return queued


async def process_one_run(
    *,
    worker_id: str | None = None,
    store: TriggerStore | None = None,
) -> dict[str, Any] | None:
    store = store or get_trigger_store()
    wid = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
    run = store.claim_next_run(worker_id=wid)
    if run is None:
        return None
    trigger = store.get_trigger(run.trigger_id)
    if trigger is None:
        run.status = "failed"
        run.result = {"error": "trigger_missing"}
        run.finished_at = _utcnow().isoformat()
        store.update_run(run)
        return {"run_id": run.id, "status": "failed", "error": "trigger_missing"}

    result = await dispatch_action(trigger, run)
    run.status = result.status  # type: ignore[assignment]
    run.result = result.result
    run.approval_id = result.approval_id
    run.ledger_entry_id = result.ledger_entry_id
    run.cost_credits = result.cost_credits
    run.quota_impact = result.quota_impact
    if result.status in {"done", "failed", "skipped", "awaiting_approval"}:
        if result.status != "awaiting_approval":
            run.finished_at = _utcnow().isoformat()
        run.locked_at = None
        run.locked_by = None
    store.update_run(run)
    return {"run_id": run.id, "trigger_id": trigger.id, "status": run.status, "result": run.result}


async def process_runs(*, limit: int = 5, worker_id: str | None = None, store: TriggerStore | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for _ in range(max(1, min(int(limit), 50))):
        item = await process_one_run(worker_id=worker_id, store=store)
        if item is None:
            break
        out.append(item)
    return out


async def tick_and_process(*, limit: int = 5, store: TriggerStore | None = None) -> dict[str, Any]:
    store = store or get_trigger_store()
    queued = tick_schedules(store)
    processed = await process_runs(limit=limit, store=store)
    return {"queued": queued, "processed": processed}


async def approve_run(run_id: str, *, store: TriggerStore | None = None):
    """Resume an awaiting_approval run by re-dispatching with approval bypass."""
    store = store or get_trigger_store()
    run = store.get_run(run_id)
    if run is None or run.status != "awaiting_approval":
        return None
    trigger = store.get_trigger(run.trigger_id)
    if trigger is None:
        return None
    # Temporarily treat as auto for this resume
    original_mode = trigger.approval_mode
    original_req = trigger.action.requires_approval
    trigger.approval_mode = "notify"
    trigger.action.requires_approval = False
    # Force non-risky path: mark approved in payload
    run.payload = {**run.payload, "approved": True}
    run.status = "running"
    store.update_run(run)
    result = await dispatch_action(trigger, run)
    trigger.approval_mode = original_mode
    trigger.action.requires_approval = original_req
    run.status = result.status  # type: ignore[assignment]
    run.result = {**result.result, "approved": True}
    run.ledger_entry_id = result.ledger_entry_id
    run.finished_at = _utcnow().isoformat() if result.status != "awaiting_approval" else None
    store.update_run(run)
    return run


def trigger_engine_enabled() -> bool:
    raw = (os.environ.get("KEPRIX_TRIGGER_ENGINE_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}
