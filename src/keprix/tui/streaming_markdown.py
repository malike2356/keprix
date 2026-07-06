"""Stable-boundary helpers for incremental markdown streaming (Hermes StreamingMd port)."""

from __future__ import annotations

import re

_CODE_FENCE_RE = re.compile(r"^(?:`{3,}|~{3,})")


def _fence_open_at(text: str, end: int) -> bool:
    code_open = False
    math_open = False
    math_opener: str | None = None
    i = 0
    while i < end:
        nl = text.find("\n", i)
        line_end = end if nl < 0 or nl > end else nl
        line = text[i:line_end].strip()

        if _CODE_FENCE_RE.match(line):
            code_open = not code_open
        elif not code_open:
            if not math_open and line.startswith("$$"):
                is_single_line = len(line) >= 4 and line.endswith("$$") and line.count("$$") >= 2
                if not is_single_line:
                    math_open = True
                    math_opener = "$$"
            elif not math_open and line.startswith("\\["):
                if not line.endswith("\\]"):
                    math_open = True
                    math_opener = "\\["
            elif math_open and math_opener == "$$" and line.endswith("$$"):
                math_open = False
                math_opener = None
            elif math_open and math_opener == "\\[" and line.endswith("\\]"):
                math_open = False
                math_opener = None

        if nl < 0 or nl >= end:
            break
        i = nl + 1

    return code_open or math_open


def find_stable_boundary(text: str) -> int:
    """Return index after the last safe paragraph boundary, or -1."""
    idx = len(text)
    while idx > 0:
        boundary = text.rfind("\n\n", 0, idx - 1)
        if boundary < 0:
            return -1
        split_at = boundary + 2
        if not _fence_open_at(text, split_at):
            return split_at
        idx = boundary
    return -1


class StreamingMarkdownState:
    """Tracks a monotonic stable prefix while markdown streams in."""

    def __init__(self) -> None:
        self.stable_prefix = ""

    def reset(self) -> None:
        self.stable_prefix = ""

    def update(self, text: str) -> tuple[str, str]:
        if not text.startswith(self.stable_prefix):
            self.stable_prefix = ""
        boundary = find_stable_boundary(text)
        if boundary > len(self.stable_prefix):
            self.stable_prefix = text[:boundary]
        return self.stable_prefix, text[len(self.stable_prefix) :]
