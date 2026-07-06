"""Hourly LLM budget alert scheduler (Prompt 148)."""

from __future__ import annotations

import asyncio
import logging

from keprix.usage.budget_alerts import check_all_workspace_budget_alerts

logger = logging.getLogger(__name__)

_task: asyncio.Task[None] | None = None
_stop = asyncio.Event()
_INTERVAL_SECONDS = 3600


async def _loop() -> None:
    while not _stop.is_set():
        try:
            sent = await check_all_workspace_budget_alerts()
            if sent:
                logger.info("Sent %d LLM budget alert(s)", sent)
        except Exception:
            logger.exception("LLM budget alert check failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=_INTERVAL_SECONDS)
        except TimeoutError:
            pass


def start_llm_budget_alert_scheduler() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    _stop.clear()
    _task = asyncio.create_task(_loop())


async def stop_llm_budget_alert_scheduler() -> None:
    global _task
    _stop.set()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
