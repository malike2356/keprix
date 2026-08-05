"""Thinking block display for keprix TUI streaming.

Renders reasoning/thinking content during streaming with a spinner,
token count, and elapsed time.  Collapses on completion.  Matches
Hermes's thinking.tsx pattern.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ThinkingBlock:
    """Tracks the state of a thinking/reasoning block during streaming."""

    content: str = ""
    is_active: bool = False
    is_collapsed: bool = False
    token_count: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0
    _last_render: str = ""

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at == 0:
            return 0.0
        end = self.ended_at if self.ended_at > 0 else time.monotonic()
        return end - self.started_at

    def start(self) -> None:
        self.is_active = True
        self.is_collapsed = False
        self.started_at = time.monotonic()
        self.content = ""
        self.token_count = 0

    def append(self, text: str) -> None:
        self.content += text
        self.token_count += 1

    def finish(self) -> None:
        self.is_active = False
        self.is_collapsed = True
        self.ended_at = time.monotonic()

    def toggle(self) -> bool:
        if self.is_collapsed:
            self.is_collapsed = False
        else:
            self.is_collapsed = True
        return self.is_collapsed

    def render(self) -> str:
        """Render the thinking block for display in the TUI."""
        if self.is_active:
            spinner = _spinner_char(int(self.elapsed_seconds * 4) % 4)
            return f"[dim italic]{spinner} Thinking... ({self.token_count} tokens, {self.elapsed_seconds:.0f}s)[/]"
        if self.is_collapsed and self.content:
            return f"[dim]Thought for {self.elapsed_seconds:.0f}s ({self.token_count} tokens) [/][italic](expand)[/]"
        if self.content:
            return self.content
        return ""


@dataclass
class ThinkingBlockManager:
    """Manages a sequence of thinking blocks in a conversation turn."""

    blocks: list[ThinkingBlock] = field(default_factory=list)
    current_block: ThinkingBlock | None = None

    def start_block(self) -> ThinkingBlock:
        block = ThinkingBlock()
        block.start()
        self.blocks.append(block)
        self.current_block = block
        return block

    def append_to_current(self, text: str) -> None:
        if self.current_block is None:
            self.current_block = self.start_block()
        self.current_block.append(text)

    def finish_current(self) -> None:
        if self.current_block:
            self.current_block.finish()
            self.current_block = None

    def all_collapsed(self) -> bool:
        return all(b.is_collapsed for b in self.blocks)

    def toggle_all(self) -> bool:
        new_state = not self.all_collapsed()
        for block in self.blocks:
            block.is_collapsed = new_state
        return new_state

    def total_thinking_time(self) -> float:
        return sum(b.elapsed_seconds for b in self.blocks if b.ended_at > 0)

    def total_thinking_tokens(self) -> int:
        return sum(b.token_count for b in self.blocks)


_SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def _spinner_char(frame: int) -> str:
    return _SPINNER_FRAMES[frame % len(_SPINNER_FRAMES)]
