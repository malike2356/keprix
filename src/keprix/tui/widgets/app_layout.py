"""Three-panel TUI layout state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppLayoutState:
    left_width: int = 28
    right_width: int = 34
    left_collapsed: bool = False
    right_collapsed: bool = False

    def effective_widths(self, total_width: int) -> tuple[int, int, int]:
        left = 0 if self.left_collapsed else min(self.left_width, max(0, total_width // 3))
        right = 0 if self.right_collapsed else min(self.right_width, max(0, total_width // 3))
        main = max(20, total_width - left - right)
        return left, main, right

    def resize_left(self, delta: int) -> None:
        self.left_width = max(18, min(60, self.left_width + delta))

    def resize_right(self, delta: int) -> None:
        self.right_width = max(22, min(80, self.right_width + delta))

