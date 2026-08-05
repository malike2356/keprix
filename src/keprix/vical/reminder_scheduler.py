"""Background tick for viCal reminders and unpaid expiry."""

from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None
_stop: asyncio.Event | None = None


def tick_seconds() -> int:
    try:
        return max(15, int(os.environ.get("KEPRIX_VICAL_REMINDER_TICK_SEC") or "60"))
    except ValueError:
        return 60


def scheduler_enabled() -> bool:
    return os.environ.get("KEPRIX_VICAL_REMINDERS", "1").strip().lower() not in {"0", "false", "no", "off"}


async def _loop() -> None:
    from keprix.vical.deposits import expire_unpaid_bookings
    from keprix.vical.reminders import process_reminders

    assert _stop is not None
    while not _stop.is_set():
        try:
            result = process_reminders()
            if result.get("count"):
                logger.info("viCal reminders sent: %s", result["count"])
        except Exception:
            logger.exception("viCal reminder tick failed")
        try:
            expire_unpaid_bookings()
        except Exception:
            logger.exception("viCal unpaid expiry failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=tick_seconds())
        except asyncio.TimeoutError:
            continue


def start_vical_reminder_scheduler() -> None:
    global _task, _stop
    if not scheduler_enabled():
        logger.info("viCal reminder scheduler disabled")
        return
    if _task and not _task.done():
        return
    _stop = asyncio.Event()
    _task = asyncio.create_task(_loop(), name="vical-reminders")
    logger.info("viCal reminder scheduler started (tick=%ss)", tick_seconds())


async def stop_vical_reminder_scheduler() -> None:
    global _task, _stop
    if _stop is not None:
        _stop.set()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=5)
        except Exception:
            _task.cancel()
    _task = None
    _stop = None
