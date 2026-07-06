"""Run queue for control center work items."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from keprix.control_center.store import get_control_center_store
from keprix.security.redactor import get_redactor

RunStatus = Literal["queued", "running", "completed", "failed"]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue_run(
    *,
    payload: dict[str, Any],
    automation_id: str | None = None,
    session_id: str | None = None,
    priority: int = 100,
) -> dict[str, Any]:
    store = get_control_center_store()
    item = {
        "id": str(uuid.uuid4()),
        "automation_id": automation_id,
        "session_id": session_id,
        "priority": priority,
        "status": "queued",
        "payload": payload,
        "logs": [],
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
    }
    store.save_queue_item(item)
    store.append_activity(
        {
            "type": "run_queued",
            "message": f"Queued run {item['id'][:8]}",
            "run_id": item["id"],
        }
    )
    return item


def start_run(run_id: str) -> dict[str, Any] | None:
    store = get_control_center_store()
    item = store.get_queue_item(run_id)
    if item is None:
        return None
    item["status"] = "running"
    item["updated_at"] = _utcnow()
    store.save_queue_item(item)
    return item


def complete_run(run_id: str, *, logs: list[str] | None = None) -> dict[str, Any] | None:
    store = get_control_center_store()
    item = store.get_queue_item(run_id)
    if item is None:
        return None
    redactor = get_redactor()
    item["status"] = "completed"
    item["logs"] = [redactor.redact(line) for line in (logs or [])]
    item["updated_at"] = _utcnow()
    store.save_queue_item(item)
    store.append_activity({"type": "run_completed", "message": f"Run {run_id[:8]} completed", "run_id": run_id})
    return public_run(item)


def fail_run(run_id: str, *, logs: list[str] | None = None) -> dict[str, Any] | None:
    store = get_control_center_store()
    item = store.get_queue_item(run_id)
    if item is None:
        return None
    redactor = get_redactor()
    item["status"] = "failed"
    item["logs"] = [redactor.redact(line) for line in (logs or ["Run failed"])]
    item["updated_at"] = _utcnow()
    store.save_queue_item(item)
    store.append_activity({"type": "run_failed", "message": f"Run {run_id[:8]} failed", "run_id": run_id})
    return public_run(item)


def public_run(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "automation_id": item.get("automation_id"),
        "session_id": item.get("session_id"),
        "priority": item.get("priority", 100),
        "status": item.get("status"),
        "payload": item.get("payload") or {},
        "logs": list(item.get("logs") or []),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
    }


def list_queue(*, status: str | None = None) -> list[dict[str, Any]]:
    queue = get_control_center_store().list_queue()
    if status:
        queue = [item for item in queue if item.get("status") == status]
    queue.sort(key=lambda row: (row.get("priority", 100), row.get("created_at", "")))
    return [public_run(item) for item in queue]
