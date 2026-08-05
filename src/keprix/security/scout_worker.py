"""Background Scout client, listener, and sync lifecycle."""

from __future__ import annotations

import asyncio
import logging

from keprix.security.scout_client import get_scout_client, refresh_scout_client
from keprix.security.scout_listener import get_scout_listener
from keprix.security.scout_sync import get_scout_sync

logger = logging.getLogger(__name__)

_stop_event: asyncio.Event | None = None
_sync_task: asyncio.Task[None] | None = None
_started = False


async def start_scout_worker() -> None:
    global _stop_event, _sync_task, _started
    if _started:
        return
    _started = True
    _stop_event = asyncio.Event()
    client = await refresh_scout_client()
    await client.start()
    listener = get_scout_listener()
    await listener.start()
    sync = get_scout_sync()
    if sync.enabled:
        _sync_task = asyncio.create_task(sync.sync_loop(_stop_event))
    try:
        from keprix.security.scout_registration import ScoutRegistration

        await ScoutRegistration().register_all_enabled_products()
    except Exception:
        logger.debug("scout product registration skipped", exc_info=True)
    logger.info(
        "scout worker started client=%s listener=%s sync=%s",
        client.enabled,
        listener.enabled,
        sync.enabled,
    )


async def stop_scout_worker() -> None:
    global _stop_event, _sync_task, _started
    if not _started:
        return
    if _stop_event is not None:
        _stop_event.set()
    if _sync_task is not None:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
        _sync_task = None
    await get_scout_listener().stop()
    await get_scout_client().stop()
    try:
        from keprix.security.scout_registration import ScoutRegistration

        reg = ScoutRegistration()
        for row in reg.list_local_registrations():
            await reg.deregister(str(row.get("product_id") or ""))
    except Exception:
        pass
    _stop_event = None
    _started = False
