"""SSE event bus for SDK action plans."""

from __future__ import annotations

import asyncio
from collections import defaultdict


class SdkEventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, app_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[app_id].append(queue)
        return queue

    def unsubscribe(self, app_id: str, queue: asyncio.Queue) -> None:
        if app_id in self._queues and queue in self._queues[app_id]:
            self._queues[app_id].remove(queue)

    async def publish(self, app_id: str, payload: dict) -> None:
        for queue in list(self._queues.get(app_id, [])):
            await queue.put(payload)


_event_bus = SdkEventBus()


def get_sdk_event_bus() -> SdkEventBus:
    return _event_bus
