"""Structured schedule next-run computation (timezone-aware)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from keprix.triggers.schema import ScheduleSpec

try:
    from croniter import croniter

    HAS_CRONITER = True
except ImportError:  # pragma: no cover
    HAS_CRONITER = False


def _tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo((name or "UTC").strip() or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _aware(dt: datetime, tz: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def compute_next_run(
    schedule: ScheduleSpec | dict[str, Any],
    *,
    timezone_name: str = "UTC",
    from_dt: datetime | None = None,
) -> datetime | None:
    """Return the next run instant (UTC-aware) after from_dt."""
    spec = schedule if isinstance(schedule, ScheduleSpec) else ScheduleSpec.from_dict(schedule)
    if spec is None:
        return None
    tz = _tz(timezone_name)
    now = _aware(from_dt or datetime.now(timezone.utc), tz)

    if spec.type == "interval":
        minutes = max(1, int(spec.every_minutes or 1))
        return (now + timedelta(minutes=minutes)).astimezone(timezone.utc)

    if spec.type == "once":
        if not spec.at:
            return None
        try:
            at = datetime.fromisoformat(spec.at.replace("Z", "+00:00"))
        except ValueError:
            return None
        at = _aware(at, tz).astimezone(timezone.utc)
        return at if at > now.astimezone(timezone.utc) else None

    if spec.type == "cron":
        expr = (spec.cron or "").strip()
        if not expr or not HAS_CRONITER:
            return None
        base = now.astimezone(tz)
        nxt = croniter(expr, base).get_next(datetime)
        return _aware(nxt, tz).astimezone(timezone.utc)

    hour = int(spec.at_hour if spec.at_hour is not None else 0)
    minute = int(spec.at_minute if spec.at_minute is not None else 0)

    if spec.type == "daily":
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate = candidate + timedelta(days=1)
        return candidate.astimezone(timezone.utc)

    if spec.type == "weekly":
        weekday = int(spec.weekday if spec.weekday is not None else 1) % 7
        # Python weekday: Mon=0 .. Sun=6; our weekday: Sun=0 .. Sat=6
        py_target = (weekday - 1) % 7
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (py_target - candidate.weekday()) % 7
        if days_ahead == 0 and candidate <= now:
            days_ahead = 7
        candidate = candidate + timedelta(days=days_ahead)
        return candidate.astimezone(timezone.utc)

    if spec.type == "monthly":
        day = max(1, min(28, int(spec.day if spec.day is not None else 1)))
        year, month = now.year, now.month
        candidate = now.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            candidate = candidate.replace(year=year, month=month, day=day)
        return candidate.astimezone(timezone.utc)

    return None


def iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
