"""Support ticket lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from keprix.support.store import get_support_store

VALID_TRANSITIONS: dict[str, set[str]] = {
    "new": {"triage", "closed"},
    "open": {"triage", "assigned", "closed"},
    "triage": {"assigned", "closed"},
    "assigned": {"investigating", "closed"},
    "investigating": {"waiting_on_customer", "resolved", "closed"},
    "waiting_on_customer": {"investigating", "resolved", "closed"},
    "resolved": {"closed", "investigating"},
    "closed": set(),
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def transition_ticket(
    ticket_id: str,
    *,
    status: str,
    actor: str,
    comment: str | None = None,
) -> dict[str, Any] | None:
    store = get_support_store()
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        return None
    current = str(ticket.get("status") or "open")
    allowed = VALID_TRANSITIONS.get(current, VALID_TRANSITIONS["open"])
    if status not in allowed and current != status:
        raise ValueError(f"Cannot transition from {current} to {status}")
    history = list(ticket.get("history") or [])
    history.append({"at": _utcnow(), "actor": actor, "from": current, "to": status, "comment": comment})
    return store.update_ticket(ticket_id, {"status": status, "history": history, "updated_at": _utcnow()})


def assign_ticket(ticket_id: str, *, assignee: str, actor: str) -> dict[str, Any] | None:
    store = get_support_store()
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        return None
    updated = transition_ticket(ticket_id, status="assigned", actor=actor, comment=f"Assigned to {assignee}")
    if updated is None:
        return None
    return store.update_ticket(ticket_id, {"assignee": assignee})


def triage_queue() -> list[dict[str, Any]]:
    tickets = get_support_store().list_tickets()
    return [ticket for ticket in tickets if ticket.get("status") in {"new", "open", "triage"}]
