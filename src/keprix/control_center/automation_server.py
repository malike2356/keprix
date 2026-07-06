"""Automation server orchestration."""

from __future__ import annotations

from typing import Any

from keprix.control_center.event_triggers import trigger_manual
from keprix.control_center.scheduled_runs import schedule_playbook_run
from keprix.control_center.store import get_control_center_store


def list_automations() -> list[dict[str, Any]]:
    automations = get_control_center_store().list_automations()
    public: list[dict[str, Any]] = []
    for automation in automations:
        public.append(
            {
                "id": automation["id"],
                "name": automation["name"],
                "trigger_type": automation["trigger_type"],
                "playbook_id": automation.get("playbook_id"),
                "server_id": automation.get("server_id"),
                "config": automation.get("config") or {},
                "enabled": automation.get("enabled", True),
                "last_run_at": automation.get("last_run_at"),
                "created_at": automation.get("created_at"),
            }
        )
    return public


def dispatch_automation(automation_id: str) -> dict[str, Any] | None:
    store = get_control_center_store()
    automation = store.get_automation(automation_id)
    if automation is None:
        return None
    trigger = automation.get("trigger_type")
    if trigger == "schedule":
        return schedule_playbook_run(automation_id)
    if trigger == "manual":
        return trigger_manual(automation_id)
    return trigger_manual(automation_id)
