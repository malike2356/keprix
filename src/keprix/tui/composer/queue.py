"""Queued prompt model."""

from __future__ import annotations

from collections import deque


class MessageQueue:
    """FIFO queue of prompts waiting while the agent is busy."""

    def __init__(self) -> None:
        self._items: deque[str] = deque()

    def __len__(self) -> int:
        return len(self._items)

    def enqueue(self, text: str) -> None:
        text = text.strip()
        if text:
            self._items.append(text)

    def pop(self) -> str | None:
        if not self._items:
            return None
        return self._items.popleft()

    def peek(self) -> str | None:
        if not self._items:
            return None
        return self._items[0]

    def clear(self) -> None:
        self._items.clear()

    def snapshot(self) -> list[str]:
        return list(self._items)


__all__ = ["MessageQueue"]
