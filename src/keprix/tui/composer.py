"""Composer helpers: message queue and input history (ported from upstream)."""

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


class InputHistory:
    """Previous submitted prompts; navigate with arrow keys."""

    def __init__(self, max_items: int = 100) -> None:
        self._items: list[str] = []
        self._max_items = max_items
        self._index = -1
        self._draft = ""

    def push(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if self._items and self._items[-1] == text:
            return
        self._items.append(text)
        if len(self._items) > self._max_items:
            self._items = self._items[-self._max_items :]
        self._index = -1
        self._draft = ""

    def begin_navigate(self, current: str) -> None:
        if self._index == -1:
            self._draft = current

    def previous(self) -> str | None:
        if not self._items:
            return None
        if self._index == -1:
            self._index = len(self._items) - 1
        elif self._index > 0:
            self._index -= 1
        return self._items[self._index]

    def next(self) -> str | None:
        if self._index < 0:
            return None
        if self._index < len(self._items) - 1:
            self._index += 1
            return self._items[self._index]
        self._index = -1
        return self._draft
