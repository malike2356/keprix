"""Periodic managed-tier allowance maintenance."""

from __future__ import annotations

import asyncio
import logging

from keprix.billing.store import get_billing_store
from keprix.billing.wallet.regrant import regrant_monthly

logger = logging.getLogger(__name__)
_task: asyncio.Task[None] | None = None
_stop = asyncio.Event()
_INTERVAL_SECONDS = 3600


async def run_regrant_once() -> int:
    granted = 0
    for subscription in await get_billing_store().list_subscriptions():
        if subscription.get("status") not in {"active", "trialing"}:
            continue
        user_id = str(subscription.get("user_id") or "").strip()
        plan_id = str(subscription.get("plan_id") or "").strip()
        if not user_id or not plan_id:
            continue
        result = await regrant_monthly(user_id, plan_id, user_id=user_id)
        if result.granted:
            granted += 1
    return granted


async def _loop() -> None:
    while not _stop.is_set():
        try:
            granted = await run_regrant_once()
            if granted:
                logger.info("Granted %d managed monthly allowance(s)", granted)
        except Exception:
            logger.exception("Managed tier allowance regrant failed")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=_INTERVAL_SECONDS)
        except TimeoutError:
            pass


def start_regrant_scheduler() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    _stop.clear()
    _task = asyncio.create_task(_loop())


async def stop_regrant_scheduler() -> None:
    global _task
    _stop.set()
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
