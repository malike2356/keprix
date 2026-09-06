"""Opt-in scheduled Scout security reviews."""

from __future__ import annotations

from typing import Any

from keprix.control_center.scheduled_runs import create_scheduled_automation, list_scheduled_automations
from keprix.control_center.store import get_control_center_store

ORDER_PLAYBOOKS = {"posture": "security-posture-review", "admin_gaps": "security-admin-gap-review", "failed_logins": "security-failed-login-review"}


def list_standing_orders() -> list[dict[str, Any]]:
    return [row for row in list_scheduled_automations() if str(row.get("name", "")).startswith("Scout security:")]


def set_standing_order(kind: str, *, enabled: bool, schedule_cron: str = "0 8 * * 1") -> dict[str, Any]:
    if kind not in ORDER_PLAYBOOKS:
        raise ValueError("unknown Scout standing order")
    if not enabled:
        return {"kind": kind, "enabled": False, "status": "disabled"}
    existing = next((row for row in list_standing_orders() if row.get("config", {}).get("kind") == kind), None)
    if existing:
        existing["enabled"] = True
        return existing
    row = create_scheduled_automation(name=f"Scout security: {kind}", playbook_id=ORDER_PLAYBOOKS[kind], schedule_cron=schedule_cron, enabled=True)
    row["config"]["kind"] = kind
    get_control_center_store().save_automation(row)
    return row
