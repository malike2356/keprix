"""Frame diff helpers."""

from dataclasses import dataclass, field

from keprix.tui.renderer.cells import CellRow, cells_from_text


@dataclass(frozen=True)
class DirtyRange:
    row: int
    start: int
    end: int


@dataclass(frozen=True)
class RenderFrame:
    rows: tuple[CellRow, ...]
    cursor: tuple[int, int] | None = None

    @classmethod
    def from_lines(cls, lines: list[str] | tuple[str, ...], *, cursor: tuple[int, int] | None = None) -> "RenderFrame":
        return cls(rows=tuple(cells_from_text(line) for line in lines), cursor=cursor)

    def snapshot(self) -> str:
        return "\n".join(row.text for row in self.rows)


@dataclass(frozen=True)
class FrameDiff:
    changed_lines: tuple[int, ...]
    dirty_ranges: tuple[DirtyRange, ...] = field(default_factory=tuple)
    cursor_changed: bool = False

    @property
    def changed(self) -> bool:
        return bool(self.changed_lines) or self.cursor_changed

    @property
    def dirty_row_count(self) -> int:
        return len(self.changed_lines)

    def debug_snapshot(self) -> str:
        ranges = ", ".join(f"{item.row}:{item.start}-{item.end}" for item in self.dirty_ranges)
        return f"dirty_rows={self.changed_lines} cursor_changed={self.cursor_changed} ranges={ranges}"


def diff_frames(previous: list[str], current: list[str]) -> FrameDiff:
    return diff_render_frames(RenderFrame.from_lines(previous), RenderFrame.from_lines(current))


def diff_render_frames(previous: RenderFrame, current: RenderFrame) -> FrameDiff:
    limit = max(len(previous.rows), len(current.rows))
    changed: list[int] = []
    ranges: list[DirtyRange] = []
    for index in range(limit):
        before = _row_text(previous, index)
        after = _row_text(current, index)
        if before == after:
            continue
        changed.append(index)
        ranges.append(_dirty_range(index, before, after))
    return FrameDiff(
        changed_lines=tuple(changed),
        dirty_ranges=tuple(ranges),
        cursor_changed=previous.cursor != current.cursor,
    )


def _dirty_range(row: int, before: str, after: str) -> DirtyRange:
    start = 0
    limit = min(len(before), len(after))
    while start < limit and before[start] == after[start]:
        start += 1
    before_end = len(before)
    after_end = len(after)
    while before_end > start and after_end > start and before[before_end - 1] == after[after_end - 1]:
        before_end -= 1
        after_end -= 1
    return DirtyRange(row=row, start=start, end=max(before_end, after_end))


def _row_text(frame: RenderFrame, index: int) -> str:
    return frame.rows[index].text if index < len(frame.rows) else ""


def _line(lines: list[str], index: int) -> str | None:
    return lines[index] if index < len(lines) else None


__all__ = ["DirtyRange", "FrameDiff", "RenderFrame", "diff_frames", "diff_render_frames"]
