"""Resize handling primitives for terminal layouts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TerminalSize:
    width: int
    height: int


def preserve_scroll(anchor_index: int, old_size: TerminalSize, new_size: TerminalSize) -> int:
    if new_size.height <= 0:
        return anchor_index
    delta = old_size.height - new_size.height
    return max(0, anchor_index + max(0, delta))

