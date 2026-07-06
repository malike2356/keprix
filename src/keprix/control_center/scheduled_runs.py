"""Scheduled automation runs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.control_center.run_queue import enqueue_run
from keprix.control_center.store import get_control_center_store

TriggerType = str


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_scheduled_automation(
    *,
    name: str,
    playbook_id: str,
    schedule_cron: str,
    server_id: str | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    store = get_control_center_store()
    automation = {
        "id": str(uuid.uuid4()),
        "name": name,
        "trigger_type": "schedule",
        "playbook_id": playbook_id,
        "server_id": server_id,
        "config": {"schedule_cron": schedule_cron},
        "enabled": enabled,
        "last_run_at": None,
        "created_at": _utcnow(),
    }
    store.save_automation(automation)
    store.append_activity(
        {
            "type": "automation_created",
            "message": f"Scheduled automation {name}",
            "automation_id": automation["id"],
        }
    )
    return automation


def schedule_playbook_run(automation_id: str) -> dict[str, Any] | None:
    store = get_control_center_store()
    automation = store.get_automation(automation_id)
    if automation is None or not automation.get("enabled"):
        return None
    run = enqueue_run(
        automation_id=automation_id,
        payload={
            "playbook_id": automation.get("playbook_id"),
            "server_id": automation.get("server_id"),
            "trigger": automation.get("trigger_type"),
        },
    )
    automation["last_run_at"] = _utcnow()
    store.save_automation(automation)
    return run


def list_scheduled_automations() -> list[dict[str, Any]]:
    automations = get_control_center_store().list_automations()
    return [item for item in automations if item.get("trigger_type") == "schedule"]
