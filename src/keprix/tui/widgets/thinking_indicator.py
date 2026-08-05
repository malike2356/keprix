"""Thinking indicator state."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThinkingIndicatorState:
    token_count: int = 0
    elapsed_sec: float = 0.0
    collapsed: bool = False

    def render(self) -> str:
        if self.collapsed:
            return f"Thinking complete ({self.token_count} tokens)"
        return f"Thinking... {self.token_count} tokens, {self.elapsed_sec:.1f}s"

