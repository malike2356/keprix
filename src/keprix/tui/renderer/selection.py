"""Selection model exports."""

from dataclasses import dataclass

from keprix.tui.selection import SelectionRange, TranscriptLineMap, TranscriptSelection, render_item_with_selection


@dataclass(frozen=True)
class HighlightSpan:
    line: int
    start: int
    end: int
    kind: str = "search"


def search_highlights(lines: list[str], query: str) -> list[HighlightSpan]:
    needle = query.lower().strip()
    if not needle:
        return []
    spans: list[HighlightSpan] = []
    for line_index, line in enumerate(lines):
        lower = line.lower()
        start = lower.find(needle)
        while start >= 0:
            spans.append(HighlightSpan(line=line_index, start=start, end=start + len(needle)))
            start = lower.find(needle, start + len(needle))
    return spans


def selected_text_from_lines(lines: list[str], selection: SelectionRange) -> str:
    (start_row, start_col), (end_row, end_col) = selection.normalized()
    if not lines:
        return ""
    start_row = max(0, min(start_row, len(lines) - 1))
    end_row = max(0, min(end_row, len(lines) - 1))
    if start_row == end_row:
        return lines[start_row][start_col:end_col]
    output = [lines[start_row][start_col:]]
    output.extend(lines[row] for row in range(start_row + 1, end_row))
    output.append(lines[end_row][:end_col])
    return "\n".join(output)


__all__ = [
    "HighlightSpan",
    "SelectionRange",
    "TranscriptLineMap",
    "TranscriptSelection",
    "render_item_with_selection",
    "search_highlights",
    "selected_text_from_lines",
]
