"""In-memory transcript history with height cache for virtual scrolling."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Literal, Sequence

from rich.console import Group
from rich.text import Text

from keprix.tui.formatting import agent_markdown, plain_text

TranscriptRole = Literal["user", "agent", "system"]

DEFAULT_MAX_ITEMS = 5000
DEFAULT_ESTIMATED_ROW_WIDTH = 72
DISPLAY_SEPARATOR = "────────────────────────────────────────"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return default


def virtual_window_size() -> int:
    return _env_int("KEPRIX_TUI_VIRTUAL_WINDOW", 120)


def virtual_overscan() -> int:
    return _env_int("KEPRIX_TUI_VIRTUAL_OVERSCAN", 8)


def _estimate_body_lines(text: str, width: int = DEFAULT_ESTIMATED_ROW_WIDTH) -> int:
    cleaned = text.strip()
    if not cleaned:
        return 1
    lines = 0
    for segment in cleaned.splitlines() or [cleaned]:
        segment = segment.strip() or " "
        lines += max(1, (len(segment) + width - 1) // width)
    return max(1, lines)


def display_lines_for_role(role: TranscriptRole, plain_text_line: str, body: str) -> list[str]:
    text = body.strip()
    if role == "user":
        body_lines = text.splitlines() if text else [""]
        return ["", "> You", *body_lines, DISPLAY_SEPARATOR]
    if role == "agent":
        body_lines = text.splitlines() if text else [""]
        return ["keprix", *body_lines, ""]
    return [plain_text_line.strip() or ""]


def display_lines_for_item(item: TranscriptItem) -> list[str]:
    plain = item.plain_text
    if item.role == "user" and plain.startswith("You: "):
        body = plain[5:]
    elif item.role == "agent" and plain.startswith("keprix: "):
        body = plain[8:]
    else:
        body = plain
    return display_lines_for_role(item.role, plain, body)


def display_line_count(role: TranscriptRole, plain_text_line: str, body: str) -> int:
    return max(1, len(display_lines_for_role(role, plain_text_line, body)))


def estimate_item_height(role: TranscriptRole, plain: str) -> int:
    body_lines = _estimate_body_lines(plain)
    if role == "user":
        return max(4, body_lines + 3)
    if role == "agent":
        return max(2, body_lines + 2)
    return max(1, body_lines)


def build_renderable(role: TranscriptRole, body: str) -> Group | Text:
    text = body.strip()
    if role == "user":
        return Group(
            Text(""),
            Text("> You", style="bold #7EE787"),
            plain_text(text),
            Text("────────────────────────────────────────", style="dim #003B00"),
        )
    if role == "agent":
        return Group(
            Text("keprix", style="bold #79C0FF"),
            agent_markdown(text),
            Text(""),
        )
    return Text(text, style="dim")


@dataclass
class TranscriptItem:
    id: str
    role: TranscriptRole
    plain_text: str
    renderable: Group | Text | None = None
    estimated_height: int = 1
    pinned: bool = False

    @classmethod
    def create(
        cls,
        *,
        role: TranscriptRole,
        plain_text: str,
        body: str | None = None,
        pinned: bool = False,
    ) -> TranscriptItem:
        content = body if body is not None else plain_text
        height = display_line_count(role, plain_text, content)
        return cls(
            id=uuid.uuid4().hex[:10],
            role=role,
            plain_text=plain_text,
            renderable=build_renderable(role, content),
            estimated_height=height,
            pinned=pinned,
        )


@dataclass
class TranscriptStore:
    """Full transcript history plus prefix-height cache."""

    max_items: int = DEFAULT_MAX_ITEMS
    items: list[TranscriptItem] = field(default_factory=list)
    prefix_heights: list[int] = field(default_factory=list)
    archived_warning: bool = False

    def clear(self) -> None:
        self.items.clear()
        self.prefix_heights.clear()
        self.archived_warning = False

    @property
    def total_height(self) -> int:
        if not self.items:
            return 0
        last = self.items[-1]
        return self.prefix_heights[-1] + last.estimated_height

    def plain_lines(self) -> list[str]:
        return [item.plain_text for item in self.items if item.plain_text.strip()]

    def full_plain_text(self) -> str:
        return "\n".join(self.plain_lines())

    def append(self, item: TranscriptItem) -> None:
        if len(self.items) >= self.max_items:
            drop = len(self.items) - self.max_items + 1
            self.items = self.items[drop:]
            self._rebuild_prefix_heights()
            self.archived_warning = True
        if not self.items:
            self.prefix_heights.append(0)
        else:
            self.prefix_heights.append(self.prefix_heights[-1] + self.items[-1].estimated_height)
        self.items.append(item)

    def update_height(self, index: int, height: int) -> None:
        if index < 0 or index >= len(self.items):
            return
        height = max(1, height)
        if self.items[index].estimated_height == height:
            return
        self.items[index].estimated_height = height
        self._rebuild_prefix_heights(from_index=index)

    def _rebuild_prefix_heights(self, from_index: int = 0) -> None:
        if not self.items:
            self.prefix_heights.clear()
            return
        if from_index <= 0:
            rebuilt = [0]
            for index in range(1, len(self.items)):
                rebuilt.append(rebuilt[-1] + self.items[index - 1].estimated_height)
            self.prefix_heights = rebuilt
            return
        while len(self.prefix_heights) < len(self.items):
            self.prefix_heights.append(0)
        for index in range(from_index, len(self.items)):
            if index == 0:
                self.prefix_heights[0] = 0
            else:
                self.prefix_heights[index] = (
                    self.prefix_heights[index - 1] + self.items[index - 1].estimated_height
                )

    def visible_index_range(
        self,
        scroll_y: int,
        viewport_height: int,
    ) -> tuple[int, int]:
        if not self.items:
            return 0, -1
        top = max(0, int(scroll_y))
        bottom = top + max(1, int(viewport_height))
        first = 0
        for index, item in enumerate(self.items):
            start = self.prefix_heights[index]
            end = start + item.estimated_height
            if end > top:
                first = index
                break
        else:
            first = len(self.items) - 1
        last = first
        for index in range(first, len(self.items)):
            if self.prefix_heights[index] >= bottom:
                break
            last = index
        return first, last

    def mount_index_range(
        self,
        scroll_y: int,
        viewport_height: int,
        *,
        max_window: int | None = None,
        overscan: int | None = None,
    ) -> tuple[int, int]:
        first, last = self.visible_index_range(scroll_y, viewport_height)
        if last < first:
            return 0, -1
        overscan_value = virtual_overscan() if overscan is None else overscan
        window_cap = virtual_window_size() if max_window is None else max_window
        start = max(0, first - overscan_value)
        end = min(len(self.items) - 1, last + overscan_value)
        while end - start + 1 > window_cap:
            trim = (end - start + 1 - window_cap + 1) // 2
            start = min(start + trim, first)
            end = max(end - trim, last)
        pinned = [index for index, item in enumerate(self.items) if item.pinned]
        if pinned:
            start = min(start, min(pinned))
            end = max(end, max(pinned))
            if end - start + 1 > window_cap:
                start = max(0, end - window_cap + 1)
        return start, end

    @staticmethod
    def prefix_heights_monotonic(prefix_heights: Sequence[int]) -> bool:
        if not prefix_heights:
            return True
        if prefix_heights[0] != 0:
            return False
        return all(prefix_heights[index] >= prefix_heights[index - 1] for index in range(1, len(prefix_heights)))


def item_from_transcript_line(line: str) -> TranscriptItem | None:
    text = line.strip()
    if not text:
        return None
    if text.startswith("You: "):
        body = text[5:]
        return TranscriptItem.create(role="user", plain_text=text, body=body)
    if text.startswith("keprix: "):
        body = text[8:]
        return TranscriptItem.create(role="agent", plain_text=text, body=body)
    return TranscriptItem.create(role="system", plain_text=text, body=text)
