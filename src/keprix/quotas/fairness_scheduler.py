"""FairnessScheduler: weighted fair-share scheduler for concurrent LLM requests.

When multiple products submit LLM requests simultaneously and the global slot
capacity is under pressure, this scheduler prioritises products that have used
a smaller fraction of their quota.

Priority formula:
  weight = (1.0 - usage_pct) + 0.1    # 0.1 floor so exhausted products still get some slots
  Higher weight = higher priority in the queue.

When slots are available (not under pressure), acquire_slot() returns immediately
with no overhead. Queuing only kicks in when max_concurrent_llm_calls is reached.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .quota_config import ResourceType
from .quota_store import QuotaStore


@dataclass
class SchedulerToken:
    """Released by the caller after the LLM call completes."""
    product_id: str
    slot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    acquired_at: float = field(default_factory=time.monotonic)

    @property
    def held_seconds(self) -> float:
        return time.monotonic() - self.acquired_at


@dataclass
class _WaitEntry:
    product_id: str
    priority: float       # higher = served first
    event: asyncio.Event = field(default_factory=asyncio.Event)
    queued_at: float = field(default_factory=time.monotonic)


class FairnessScheduler:
    """Weighted fair-share scheduler for concurrent LLM requests.

    Usage::

        scheduler = FairnessScheduler(max_slots=8, store=store)
        token = await scheduler.acquire_slot("aiva")
        try:
            response = await llm_client.call(...)
        finally:
            await scheduler.release_slot(token)
    """

    def __init__(
        self,
        max_slots: int = 8,
        max_per_product: int = 3,
        store: QuotaStore | None = None,
    ) -> None:
        self._max_slots = max_slots
        self._max_per_product = max_per_product
        self._store = store
        self._active_slots: int = 0
        self._per_product: dict[str, int] = {}
        self._queue: list[_WaitEntry] = []
        self._lock = asyncio.Lock()

    async def _compute_priority(self, product_id: str) -> float:
        """Priority = remaining quota pct. Low usage -> high priority."""
        if self._store is None:
            return 0.5
        try:
            usage = await self._store.get_usage(product_id)
            pct = usage.pct_used(ResourceType.LLM_TOKENS_IN)
            return (1.0 - pct) + 0.1   # 0.1 floor ensures exhausted products still proceed
        except Exception:
            return 0.5

    async def _try_dispatch(self) -> None:
        """Try to dispatch the highest-priority waiting entry if a slot is free."""
        if not self._queue:
            return
        if self._active_slots >= self._max_slots:
            return

        # Sort queue: highest priority first, then oldest
        self._queue.sort(key=lambda e: (-e.priority, e.queued_at))

        for entry in self._queue:
            per_prod = self._per_product.get(entry.product_id, 0)
            if per_prod >= self._max_per_product:
                continue
            # Found one to dispatch
            self._queue.remove(entry)
            self._active_slots += 1
            self._per_product[entry.product_id] = per_prod + 1
            entry.event.set()
            return

    async def acquire_slot(self, product_id: str) -> SchedulerToken:
        """Acquire an LLM slot. May wait if all slots are occupied."""
        async with self._lock:
            per_prod = self._per_product.get(product_id, 0)
            # Fast path: slots available and product not at its per-product cap
            if (
                self._active_slots < self._max_slots
                and per_prod < self._max_per_product
            ):
                self._active_slots += 1
                self._per_product[product_id] = per_prod + 1
                return SchedulerToken(product_id=product_id)

            # Slow path: queue the request
            priority = await self._compute_priority(product_id)
            entry = _WaitEntry(product_id=product_id, priority=priority)
            self._queue.append(entry)

        # Wait outside the lock
        await entry.event.wait()
        return SchedulerToken(product_id=product_id)

    async def release_slot(self, token: SchedulerToken) -> None:
        """Release an LLM slot after the call completes."""
        async with self._lock:
            self._active_slots = max(0, self._active_slots - 1)
            per = self._per_product.get(token.product_id, 1)
            self._per_product[token.product_id] = max(0, per - 1)
            await self._try_dispatch()

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of scheduler state (no lock; approximate for dashboards)."""
        return {
            "active_slots": self._active_slots,
            "max_slots": self._max_slots,
            "queued_requests": len(self._queue),
            "per_product": dict(self._per_product),
        }
