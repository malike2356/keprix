"""Cooperative wait/signal for mutation approval during open chat streams."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field

from keprix.agent.keprix.store import get_generated_tool_store

logger = logging.getLogger(__name__)

MutationWaitResolution = str  # approved | rejected | timeout


@dataclass
class _MutationWaiter:
    record_id: str
    event: threading.Event = field(default_factory=threading.Event)
    resolution: MutationWaitResolution | None = None
    registered_at: float = field(default_factory=time.time)


_WAITERS: dict[str, _MutationWaiter] = {}
_LOCK = threading.Lock()


def register_mutation_wait_now(record_id: str) -> None:
    """Register a waiter synchronously (safe before yielding stream events)."""
    with _LOCK:
        _WAITERS[record_id] = _MutationWaiter(record_id=record_id)
    logger.debug("mutation wait registered for %s", record_id)


async def register_mutation_wait(record_id: str) -> None:
    register_mutation_wait_now(record_id)


async def unregister_mutation_wait(record_id: str) -> None:
    with _LOCK:
        _WAITERS.pop(record_id, None)


def has_active_mutation_wait(record_id: str) -> bool:
    with _LOCK:
        return record_id in _WAITERS


async def signal_mutation_resolved(record_id: str, resolution: MutationWaitResolution) -> bool:
    with _LOCK:
        waiter = _WAITERS.get(record_id)
        if waiter is None:
            return False
        waiter.resolution = resolution
        waiter.event.set()
    logger.debug("mutation wait signaled %s -> %s", record_id, resolution)
    return True


async def wait_for_mutation_resolution(
    record_id: str,
    *,
    timeout_s: float,
    poll_interval_s: float = 0.25,
) -> MutationWaitResolution:
    """Wait until approval/rejection, timeout, or store status change."""
    deadline = time.time() + timeout_s
    store = get_generated_tool_store()

    with _LOCK:
        waiter = _WAITERS.get(record_id)

    while time.time() < deadline:
        record = store.get(record_id)
        if record is not None:
            if record.status == "installed":
                return "approved"
            if record.status == "rejected":
                return "rejected"

        if waiter is not None:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            signaled = await asyncio.to_thread(waiter.event.wait, min(poll_interval_s, remaining))
            if signaled and waiter.resolution in {"approved", "rejected"}:
                return waiter.resolution
            continue

        await asyncio.sleep(poll_interval_s)

    return "timeout"
