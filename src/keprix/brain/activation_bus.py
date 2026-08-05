"""In-memory brain activation pub/sub."""

from __future__ import annotations

import asyncio
from typing import Any


class ActivationBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = {}

    def subscribe(self, workspace_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._queues.setdefault(workspace_id, []).append(queue)
        return queue

    def unsubscribe(self, workspace_id: str, queue: asyncio.Queue) -> None:
        queues = self._queues.get(workspace_id, [])
        if queue in queues:
            queues.remove(queue)

    async def publish(self, workspace_id: str, event: dict[str, Any]) -> None:
        for queue in list(self._queues.get(workspace_id, [])):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue


activation_bus = ActivationBus()
