"""On-demand history loading for large TUI sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from keprix.tui.message_types import TuiMessage


class HistorySource(Protocol):
    def count(self, session_id: str) -> int: ...
    def load(self, session_id: str, *, offset: int, limit: int) -> list[TuiMessage]: ...


@dataclass(frozen=True)
class HistoryWindow:
    offset: int
    total: int
    messages: list[TuiMessage]


class InMemoryHistorySource:
    def __init__(self, messages: list[TuiMessage] | None = None) -> None:
        self._messages = list(messages or [])

    def append(self, message: TuiMessage) -> None:
        self._messages.append(message)

    def count(self, session_id: str) -> int:
        return len(self._messages)

    def load(self, session_id: str, *, offset: int, limit: int) -> list[TuiMessage]:
        return self._messages[max(0, offset) : max(0, offset) + max(0, limit)]


class VirtualHistory:
    def __init__(self, source: HistorySource, *, page_size: int = 200) -> None:
        self.source = source
        self.page_size = page_size

    def window(self, session_id: str, *, anchor: int, visible_count: int) -> HistoryWindow:
        total = self.source.count(session_id)
        limit = max(visible_count, self.page_size)
        offset = max(0, min(anchor, max(0, total - limit)))
        return HistoryWindow(offset=offset, total=total, messages=self.source.load(session_id, offset=offset, limit=limit))
