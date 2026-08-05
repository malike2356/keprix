"""Large paste collapse for the TUI composer (Prompt 206)."""

from __future__ import annotations

PASTE_COLLAPSE_THRESHOLD = 2000


def collapsed_paste_placeholder(line_count: int) -> str:
    return f"[Pasted {line_count} lines, expanded on send]"


def should_collapse_paste(text: str) -> bool:
    return len(text) >= PASTE_COLLAPSE_THRESHOLD


def line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + 1


class PasteSnipStore:
    """Maps composer placeholder text to full pasted content."""

    def __init__(self) -> None:
        self._snips: dict[str, str] = {}

    def store(self, placeholder: str, full_text: str) -> None:
        self._snips[placeholder] = full_text

    def expand(self, text: str) -> str:
        return self._snips.get(text, text)

    def clear(self) -> None:
        self._snips.clear()
