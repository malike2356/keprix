"""Background Governance heartbeat and event flush loops."""

from __future__ import annotations

import asyncio
import logging

from keprix.governance.client import get_governance_client
from keprix.governance.event_reporter import flush_events
from keprix.governance.heartbeat import run_heartbeat_if_enabled
from keprix.governance.policy_receiver import reload_policies

logger = logging.getLogger(__name__)

_heartbeat_task: asyncio.Task[None] | None = None
_flush_task: asyncio.Task[None] | None = None
_stop_event: asyncio.Event | None = None


async def _heartbeat_loop() -> None:
    assert _stop_event is not None
    client = get_governance_client()
    while not _stop_event.is_set():
        try:
            api_key = await client.resolve_api_key(user_id="system")
            await run_heartbeat_if_enabled(api_key)
        except Exception:
            logger.exception("governance heartbeat failed")
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=60.0)
        except TimeoutError:
            pass


async def _flush_loop() -> None:
    assert _stop_event is not None
    client = get_governance_client()
    while not _stop_event.is_set():
        try:
            api_key = await client.resolve_api_key(user_id="system")
            await flush_events(api_key=api_key)
        except Exception:
            logger.exception("governance event flush failed")
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=10.0)
        except TimeoutError:
            pass


def start_governance_worker() -> None:
    global _heartbeat_task, _flush_task, _stop_event
    if _heartbeat_task is not None and not _heartbeat_task.done():
        return
    _stop_event = asyncio.Event()
    _heartbeat_task = asyncio.create_task(_heartbeat_loop())
    _flush_task = asyncio.create_task(_flush_loop())
    asyncio.create_task(reload_policies())


async def stop_governance_worker() -> None:
    global _heartbeat_task, _flush_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    tasks = [task for task in (_heartbeat_task, _flush_task) if task is not None]
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    _heartbeat_task = None
    _flush_task = None
    _stop_event = None
