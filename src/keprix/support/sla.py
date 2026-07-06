"""SLA tracking for support tickets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DEFAULT_SLA_HOURS = {"critical": 4, "high": 8, "normal": 24, "low": 72}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def sla_status(ticket: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    priority = str(ticket.get("priority") or "normal").lower()
    hours = DEFAULT_SLA_HOURS.get(priority, 24)
    created = _parse_iso(str(ticket.get("created_at")))
    now = now or datetime.now(timezone.utc)
    elapsed_hours = (now - created).total_seconds() / 3600
    remaining = hours - elapsed_hours
    breached = remaining < 0 and ticket.get("status") not in {"resolved", "closed"}
    return {
        "priority": priority,
        "sla_hours": hours,
        "elapsed_hours": round(elapsed_hours, 2),
        "remaining_hours": round(remaining, 2),
        "breached": breached,
        "at_risk": not breached and remaining < hours * 0.25,
    }
