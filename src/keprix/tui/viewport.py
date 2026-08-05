"""Virtual viewport tracking for keprix TUI transcripts.

Provides viewport state management for scrolling, auto-scroll toggling,
and scroll position preservation across resize events.  Used by the
virtual transcript widget to render only visible messages.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ViewportState:
    """Tracks scroll position and viewport dimensions."""

    scroll_offset: int = 0
    viewport_height: int = 0
    content_height: int = 0
    auto_scroll: bool = True  # Follow new messages by default
    at_bottom: bool = True
    anchor_message_index: int = -1  # Message to keep visible during resize

    def update_dimensions(self, viewport_height: int, content_height: int) -> None:
        """Update dimensions, preserving relative scroll position if anchored."""
        old_height = self.viewport_height
        self.viewport_height = viewport_height
        self.content_height = content_height

        # If we were at bottom, stay at bottom
        if self.at_bottom:
            self.scroll_offset = max(0, content_height - viewport_height)
            return

        # If anchored to a message, keep it visible
        if self.anchor_message_index >= 0 and old_height > 0:
            ratio = self.scroll_offset / (self.content_height - old_height) if self.content_height > old_height else 0
            self.scroll_offset = max(0, int(ratio * (content_height - viewport_height)))

        self.scroll_offset = min(self.scroll_offset, max(0, content_height - viewport_height))
        self.at_bottom = self.scroll_offset >= (content_height - viewport_height - 1)

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll down by N lines."""
        max_offset = max(0, self.content_height - self.viewport_height)
        self.scroll_offset = min(self.scroll_offset + lines, max_offset)
        self.at_bottom = self.scroll_offset >= max_offset
        self.anchor_message_index = -1

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll up by N lines. Disables auto-scroll."""
        self.scroll_offset = max(0, self.scroll_offset - lines)
        self.at_bottom = False
        self.auto_scroll = False
        self.anchor_message_index = -1

    def scroll_to(self, offset: int) -> None:
        """Scroll to a specific offset."""
        max_offset = max(0, self.content_height - self.viewport_height)
        self.scroll_offset = max(0, min(offset, max_offset))
        self.at_bottom = self.scroll_offset >= max_offset
        self.anchor_message_index = -1

    def scroll_to_bottom(self) -> None:
        """Scroll to bottom, re-enabling auto-scroll."""
        self.scroll_offset = max(0, self.content_height - self.viewport_height)
        self.at_bottom = True
        self.auto_scroll = True
        self.anchor_message_index = -1

    def scroll_to_top(self) -> None:
        """Scroll to top, disabling auto-scroll."""
        self.scroll_offset = 0
        self.at_bottom = False
        self.auto_scroll = False
        self.anchor_message_index = -1

    def anchor_to_message(self, message_index: int) -> None:
        """Keep this message visible during resize events."""
        self.anchor_message_index = message_index

    def toggle_auto_scroll(self) -> bool:
        """Toggle auto-scroll. Returns new state."""
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self.scroll_to_bottom()
        return self.auto_scroll

    def visible_range(self) -> tuple[int, int]:
        """Return the (first_visible_line, last_visible_line) range."""
        return (self.scroll_offset, self.scroll_offset + self.viewport_height)

    def is_line_visible(self, line_index: int) -> bool:
        """Check if a line is within the visible viewport."""
        return self.scroll_offset <= line_index < (self.scroll_offset + self.viewport_height)
