"""Durable outreach campaign / sequence scheduler (Prompt 624).

Claim-lease ticks; Soft Wall park; backoff; no in-memory timers.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, time, timezone
from typing import Any, TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from keprix.outreach.service import OutreachService

DEFAULT_MAX_ATTEMPTS = 8
DEFAULT_LEASE_SECONDS = 60


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def next_open_business_window(tz_name: str, now: datetime | None = None) -> datetime:
    """Next Mon-Fri 09:00 in campaign TZ (UTC-aware), when outside the open window."""
    try:
        tz = ZoneInfo(tz_name or "Europe/London")
    except Exception:
        tz = ZoneInfo("Europe/London")
    local = (now or _utcnow()).astimezone(tz)
    candidate = local.replace(hour=9, minute=0, second=0, microsecond=0)
    if local.weekday() < 5 and local.time() < time(9, 0):
        return candidate.astimezone(timezone.utc)
    day = local.date() + timedelta(days=1)
    while True:
        nxt = datetime.combine(day, time(9, 0), tzinfo=tz)
        if nxt.weekday() < 5:
            return nxt.astimezone(timezone.utc)
        day += timedelta(days=1)


def next_midnight_in_tz(tz_name: str, now: datetime | None = None) -> datetime:
    try:
        tz = ZoneInfo(tz_name or "Europe/London")
    except Exception:
        tz = ZoneInfo("Europe/London")
    local = (now or _utcnow()).astimezone(tz)
    tomorrow = local.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0, 0), tzinfo=tz).astimezone(timezone.utc)


def backoff_seconds(attempt_count: int) -> float:
    base = min(2 ** max(0, int(attempt_count)), 3600)
    return float(base) + random.uniform(0, 5)


def run_scheduler_tick(
    workspace_id: str | None = None,
    *,
    limit: int = 50,
    now: datetime | None = None,
    dry_run: bool | None = None,
    worker_id: str | None = None,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    service: OutreachService | None = None,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Claim due enrollments and process one tick. Used by HTTP + tools + CLI."""
    from keprix.outreach.service import get_outreach_service

    svc = service or get_outreach_service()
    return svc.process_due(
        workspace_id,
        limit=limit,
        now=now,
        dry_run=dry_run,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        max_attempts=max_attempts,
    )
