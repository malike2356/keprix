"""Small condition DSL and live viCal -> lead workflow."""

from __future__ import annotations

import os
from typing import Any


def _dig(payload: dict[str, Any], path: str) -> Any:
    cur: Any = payload
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def eval_condition(condition: dict[str, Any], event: dict[str, Any]) -> bool:
    """Supported ops: eq, ne, present, in."""
    op = str(condition.get("op") or "eq").lower()
    field = str(condition.get("field") or "")
    value = condition.get("value")
    actual = _dig(event, field) if field else None
    if op == "eq":
        return actual == value
    if op == "ne":
        return actual != value
    if op == "present":
        return actual not in (None, "", [], {})
    if op == "in":
        return actual in (value or [])
    return False


def eval_all(conditions: list[dict[str, Any]], event: dict[str, Any]) -> bool:
    return all(eval_condition(c, event) for c in conditions)


BOOKING_CONFIRMED_TO_LEAD = {
    "id": "vical_confirmed_create_lead",
    "when": [{"op": "eq", "field": "status", "value": "confirmed"}],
    "actions": [
        {"type": "create_lead", "from": {"name": "guest_name", "email": "guest_email"}},
        {"type": "link_booking_to_lead"},
    ],
    "dry_run_notes": "Fires when a viCal booking status becomes confirmed.",
}


def dry_run_booking_confirmed(event: dict[str, Any]) -> dict[str, Any]:
    matched = eval_all(BOOKING_CONFIRMED_TO_LEAD["when"], event)  # type: ignore[arg-type]
    actions: list[dict[str, Any]] = []
    if matched:
        actions.append(
            {
                "type": "create_lead",
                "name": event.get("guest_name"),
                "email": event.get("guest_email"),
            }
        )
        if event.get("id"):
            actions.append({"type": "link_booking_to_lead", "booking_id": event.get("id")})
    return {"matched": matched, "actions": actions, "template": BOOKING_CONFIRMED_TO_LEAD["id"]}


def workflow_auto_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_LEAD_WORKFLOW", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def execute_booking_confirmed_workflow(event: dict[str, Any]) -> dict[str, Any]:
    """Create/link a lead when a booking is confirmed (real store writes)."""
    plan = dry_run_booking_confirmed(event)
    if not plan["matched"] or not workflow_auto_enabled():
        return {**plan, "executed": False}
    from keprix.product_leads.store import get_lead_store

    store = get_lead_store()
    lead = store.create(
        name=str(event.get("guest_name") or "Guest").strip() or "Guest",
        email=str(event.get("guest_email") or ""),
        contact_id=event.get("contact_id"),
        tenant_id=event.get("tenant_id"),
        metadata={"source": "vical_confirmed_workflow", "booking_id": event.get("id")},
    )
    booking_id = event.get("id")
    if booking_id:
        lead = store.link_booking(lead["id"], str(booking_id))
    return {**plan, "executed": True, "lead": lead}
