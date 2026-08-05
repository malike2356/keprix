"""In-memory log viewer model for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LogEntry:
    level: str
    message: str


class LogViewerBuffer:
    def __init__(self, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self._entries: list[LogEntry] = []

    def append(self, level: str, message: str) -> None:
        self._entries.append(LogEntry(level=level.upper(), message=message))
        self._entries[:] = self._entries[-self.max_entries :]

    def filter(self, *, level: str | None = None, query: str = "") -> list[LogEntry]:
        entries = self._entries
        if level:
            entries = [entry for entry in entries if entry.level == level.upper()]
        if query:
            needle = query.lower()
            entries = [entry for entry in entries if needle in entry.message.lower()]
        return list(entries)

