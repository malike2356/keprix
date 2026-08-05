"""Search helpers for transcript history."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.tui.message_types import TuiMessage


@dataclass(frozen=True)
class HistoryMatch:
    index: int
    start: int
    end: int
    excerpt: str


def search_history(messages: list[TuiMessage], query: str) -> list[HistoryMatch]:
    needle = query.lower().strip()
    if not needle:
        return []
    matches: list[HistoryMatch] = []
    for index, message in enumerate(messages):
        content = message.content or ""
        pos = content.lower().find(needle)
        if pos >= 0:
            start = max(0, pos - 40)
            end = min(len(content), pos + len(query) + 40)
            matches.append(HistoryMatch(index=index, start=pos, end=pos + len(query), excerpt=content[start:end]))
    return matches

