"""Focus management for keprix TUI widgets.

Provides a simple focus stack that Textual widgets can use to track
which widget currently has keyboard focus.  Defines named focus zones
so keyboard shortcuts can be context-aware.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar


class FocusZone(Enum):
    """Named focus zones in the TUI layout."""

    INPUT = auto()         # The main text input
    TRANSCRIPT = auto()    # The message transcript view
    SIDEBAR = auto()       # The session/panel sidebar
    OVERLAY = auto()       # Any modal overlay
    NONE = auto()          # No focus (startup)


@dataclass
class FocusState:
    """Tracks the current focus zone and history."""

    current: FocusZone = FocusZone.NONE
    previous: FocusZone = FocusZone.NONE

    def set(self, zone: FocusZone) -> None:
        """Set focus to a new zone, recording the previous."""
        if self.current != zone:
            self.previous = self.current
            self.current = zone

    def restore_previous(self) -> FocusZone:
        """Restore the previous focus zone."""
        prev = self.previous
        self.previous = self.current
        self.current = prev
        return self.current


# Global focus state for the TUI process (single instance).
_focus_state: FocusZone = FocusZone.NONE
_previous_focus: FocusZone = FocusZone.NONE


def set_focus(zone: FocusZone) -> None:
    """Update the global focus zone."""
    global _focus_state, _previous_focus
    if _focus_state != zone:
        _previous_focus = _focus_state
        _focus_state = zone


def get_focus() -> FocusZone:
    """Return the current focus zone."""
    return _focus_state


def restore_focus() -> FocusZone:
    """Restore the previous focus zone."""
    global _focus_state, _previous_focus
    prev = _previous_focus
    _previous_focus = _focus_state
    _focus_state = prev
    return _focus_state


def is_input_focused() -> bool:
    return _focus_state == FocusZone.INPUT


def is_overlay_active() -> bool:
    return _focus_state == FocusZone.OVERLAY
