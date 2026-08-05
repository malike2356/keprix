"""Background calendar auto-sync scheduler (per-source intervals, 2-way)."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None
_stop: asyncio.Event | None = None

DEFAULT_INTERVAL_MINUTES = 15
MIN_INTERVAL_MINUTES = 1
MAX_INTERVAL_MINUTES = 24 * 60
DEFAULT_TICK_SECONDS = 30


def clamp_sync_interval_minutes(value: Any, default: int = DEFAULT_INTERVAL_MINUTES) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = default
    return max(MIN_INTERVAL_MINUTES, min(MAX_INTERVAL_MINUTES, minutes))


def _as_aware(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def source_is_due(source: dict[str, Any], *, now: datetime | None = None) -> bool:
    if source.get("enabled") is False:
        return False
    if source.get("auto_sync", True) is False:
        return False
    now = now or datetime.now(timezone.utc)
    last = _as_aware(source.get("last_sync_at"))
    if last is None:
        return True
    interval = clamp_sync_interval_minutes(source.get("sync_interval_minutes"))
    return last + timedelta(minutes=interval) <= now


def next_sync_at(source: dict[str, Any]) -> datetime | None:
    if source.get("enabled") is False or source.get("auto_sync", True) is False:
        return None
    last = _as_aware(source.get("last_sync_at"))
    interval = clamp_sync_interval_minutes(source.get("sync_interval_minutes"))
    if last is None:
        return datetime.now(timezone.utc)
    return last + timedelta(minutes=interval)


def auto_sync_enabled_globally() -> bool:
    raw = os.environ.get("KEPRIX_CALENDAR_AUTO_SYNC", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def tick_seconds() -> int:
    try:
        return max(5, int(os.environ.get("KEPRIX_CALENDAR_SYNC_TICK_SEC") or DEFAULT_TICK_SECONDS))
    except ValueError:
        return DEFAULT_TICK_SECONDS


async def run_due_sources(repo: Any | None = None) -> dict[str, Any]:
    """Sync every due enabled source once. Used by scheduler and tests."""
    from keprix.workspace.calendar_sync import sync_one_source
    from keprix.workspace.repository import workspace_repo

    store = repo or workspace_repo
    due = store.list_due_caldav_sources()
    synced = 0
    errors = 0
    results: list[dict[str, Any]] = []
    for source in due:
        user = {"id": source["user_id"]}
        try:
            outcome = await sync_one_source(user, source, store)
            store.mark_source_synced(user, source["id"], ok=True, message=outcome.get("message"))
            synced += 1
            results.append(outcome)
        except Exception as exc:
            errors += 1
            message = str(exc)
            logger.exception("auto calendar sync failed for %s", source.get("id"))
            try:
                store.mark_source_synced(user, source["id"], ok=False, message=message)
            except Exception:
                pass
            results.append({"source_id": source.get("id"), "ok": False, "error": message})
    return {"ok": errors == 0, "due": len(due), "synced": synced, "errors": errors, "results": results}


async def _loop() -> None:
    assert _stop is not None
    while not _stop.is_set():
        if auto_sync_enabled_globally():
            try:
                summary = await run_due_sources()
                if summary.get("due"):
                    logger.info(
                        "calendar auto-sync tick due=%s synced=%s errors=%s",
                        summary.get("due"),
                        summary.get("synced"),
                        summary.get("errors"),
                    )
            except Exception:
                logger.exception("calendar auto-sync tick failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=tick_seconds())
        except TimeoutError:
            pass


def start_calendar_sync_scheduler() -> asyncio.Task[None] | None:
    global _task, _stop
    if not auto_sync_enabled_globally():
        logger.info("calendar auto-sync scheduler disabled via KEPRIX_CALENDAR_AUTO_SYNC")
        return None
    if _task is not None and not _task.done():
        return _task
    _stop = asyncio.Event()
    _task = asyncio.create_task(_loop(), name="keprix-calendar-auto-sync")
    logger.info("calendar auto-sync scheduler started (tick=%ss)", tick_seconds())
    return _task


async def stop_calendar_sync_scheduler() -> None:
    global _task, _stop
    if _stop is not None:
        _stop.set()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=5)
        except TimeoutError:
            _task.cancel()
        _task = None
    _stop = None


def scheduler_status() -> dict[str, Any]:
    running = _task is not None and not _task.done()
    return {
        "enabled": auto_sync_enabled_globally(),
        "running": running,
        "tick_seconds": tick_seconds(),
        "default_interval_minutes": DEFAULT_INTERVAL_MINUTES,
        "min_interval_minutes": MIN_INTERVAL_MINUTES,
        "max_interval_minutes": MAX_INTERVAL_MINUTES,
    }
