"""Transcript text selection for the TUI (upstream-style line coordinates)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from rich.console import Group
from rich.text import Text

from keprix.tui.transcript_store import (
    TranscriptItem,
    TranscriptStore,
    display_lines_for_item,
)


def copy_on_select_enabled() -> bool:
    raw = os.environ.get("KEPRIX_TUI_COPY_ON_SELECT", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}

    program = os.environ.get("TERM_PROGRAM", "").lower()
    return program in {"apple_terminal", "iterm.app", "vscode"}


@dataclass
class TranscriptLineMap:
    lines: list[str]
    item_starts: list[int]

    @classmethod
    def from_store(cls, store: TranscriptStore) -> TranscriptLineMap:
        lines: list[str] = []
        item_starts: list[int] = []
        for item in store.items:
            item_starts.append(len(lines))
            lines.extend(display_lines_for_item(item))
        return cls(lines=lines, item_starts=item_starts)

    @property
    def line_count(self) -> int:
        return len(self.lines)


@dataclass
class SelectionRange:
    start: tuple[int, int]
    end: tuple[int, int]

    @classmethod
    def collapsed(cls, row: int, col: int) -> SelectionRange:
        return cls((row, col), (row, col))

    def normalized(self) -> tuple[tuple[int, int], tuple[int, int]]:
        start = self.start
        end = self.end
        if start > end:
            start, end = end, start
        return start, end

    def is_empty(self) -> bool:
        return self.start == self.end


class TranscriptSelection:
    """Line/column selection over flattened transcript display lines."""

    def __init__(self) -> None:
        self._anchor: tuple[int, int] | None = None
        self._range = SelectionRange.collapsed(0, 0)
        self._active = False

    def clear(self) -> None:
        self._anchor = None
        self._range = SelectionRange.collapsed(0, 0)
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active and not self._range.is_empty()

    @property
    def anchor(self) -> tuple[int, int] | None:
        return self._anchor

    def start_at(self, row: int, col: int, *, extend: bool = False) -> None:
        row = max(0, row)
        col = max(0, col)
        if extend and self._anchor is not None:
            self._range = SelectionRange(self._anchor, (row, col))
        else:
            self._anchor = (row, col)
            self._range = SelectionRange.collapsed(row, col)
        self._active = True

    def extend_to(self, row: int, col: int) -> None:
        row = max(0, row)
        col = max(0, col)
        anchor = self._anchor or self._range.start
        self._anchor = anchor
        self._range = SelectionRange(anchor, (row, col))
        self._active = True

    def extend_by_arrow(self, row_delta: int, col_delta: int, line_map: TranscriptLineMap) -> None:
        if not line_map.lines:
            return
        anchor = self._anchor or self._range.end
        end_row, end_col = self._range.end
        if self._anchor is None:
            end_row, end_col = anchor
        new_row = min(max(0, end_row + row_delta), max(0, len(line_map.lines) - 1))
        line = line_map.lines[new_row]
        new_col = end_col + col_delta
        if new_col < 0:
            new_col = 0
        elif new_col > len(line):
            new_col = len(line)
        if self._anchor is None:
            self._anchor = anchor
        self.extend_to(new_row, new_col)

    def cell_at(
        self,
        *,
        local_y: float,
        local_x: float,
        scroll_y: int,
        line_map: TranscriptLineMap,
        padding_top: int = 1,
        padding_left: int = 2,
    ) -> tuple[int, int]:
        if not line_map.lines:
            return 0, 0
        row = int(scroll_y + local_y - padding_top)
        row = min(max(0, row), len(line_map.lines) - 1)
        col = int(local_x - padding_left)
        col = min(max(0, col), len(line_map.lines[row]))
        return row, col

    def selected_text(self, line_map: TranscriptLineMap) -> str:
        if not self.is_active or not line_map.lines:
            return ""
        (start_row, start_col), (end_row, end_col) = self._range.normalized()
        if start_row == end_row:
            line = line_map.lines[start_row]
            return line[start_col:end_col]
        chunks: list[str] = []
        for row in range(start_row, end_row + 1):
            line = line_map.lines[row]
            if row == start_row:
                chunks.append(line[start_col:])
            elif row == end_row:
                chunks.append(line[:end_col])
            else:
                chunks.append(line)
        return "\n".join(chunks).strip("\n")

    def line_style(self, line_index: int, line_text: str) -> Text | str:
        if not self.is_active:
            return line_text
        (start_row, start_col), (end_row, end_col) = self._range.normalized()
        if line_index < start_row or line_index > end_row:
            return line_text
        if start_row == end_row:
            return _styled_segment(line_text, start_col, end_col)
        if line_index == start_row:
            return _styled_segment(line_text, start_col, len(line_text))
        if line_index == end_row:
            return _styled_segment(line_text, 0, end_col)
        return Text(line_text, style="reverse")


def _styled_segment(line: str, start_col: int, end_col: int) -> Text:
    start_col = max(0, min(start_col, len(line)))
    end_col = max(start_col, min(end_col, len(line)))
    text = Text()
    if start_col:
        text.append(line[:start_col])
    if end_col > start_col:
        text.append(line[start_col:end_col], style="reverse")
    if end_col < len(line):
        text.append(line[end_col:])
    return text


def render_item_with_selection(
    item: TranscriptItem,
    item_index: int,
    line_map: TranscriptLineMap,
    selection: TranscriptSelection,
) -> Group | Text:
    if not selection.is_active:
        return item.renderable or Text(item.plain_text)
    lines = display_lines_for_item(item)
    start_line = line_map.item_starts[item_index] if item_index < len(line_map.item_starts) else 0
    parts: list[Text] = []
    for offset, line in enumerate(lines):
        styled_line = selection.line_style(start_line + offset, line)
        parts.append(styled_line if isinstance(styled_line, Text) else Text(str(styled_line)))
    return Group(*parts)

