"""Alternate screen and terminal state management for keprix TUI.

Matches Hermes's AlternateScreen.tsx pattern.  Textual already manages
the alternate screen via its App class, but this module provides
explicit control for edge cases where Textual's management needs help.
"""

from __future__ import annotations

import sys


def enter_alternate_screen() -> None:
    """Enter the alternate screen buffer (full-screen mode)."""
    try:
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()
    except Exception:
        pass


def exit_alternate_screen() -> None:
    """Exit the alternate screen buffer, restore the main screen."""
    try:
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
    except Exception:
        pass


def save_cursor() -> None:
    """Save cursor position."""
    try:
        sys.stdout.write("\033[s")
        sys.stdout.flush()
    except Exception:
        pass


def restore_cursor() -> None:
    """Restore cursor position."""
    try:
        sys.stdout.write("\033[u")
        sys.stdout.flush()
    except Exception:
        pass


def hide_cursor() -> None:
    """Hide the terminal cursor."""
    try:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    except Exception:
        pass


def show_cursor() -> None:
    """Show the terminal cursor."""
    try:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
    except Exception:
        pass


def clear_screen() -> None:
    """Clear the entire screen."""
    try:
        sys.stdout.write("\033[2J")
        sys.stdout.flush()
    except Exception:
        pass


def clear_to_end_of_screen() -> None:
    """Clear from cursor to end of screen."""
    try:
        sys.stdout.write("\033[0J")
        sys.stdout.flush()
    except Exception:
        pass


def set_window_title(title: str) -> None:
    """Set the terminal window title."""
    if not title:
        return
    safe_title = title.replace("\033", "").replace("\x07", "")
    try:
        sys.stdout.write(f"\033]0;{safe_title}\x07")
        sys.stdout.flush()
    except Exception:
        pass


def ring_bell() -> None:
    """Ring the terminal bell (for notifications)."""
    try:
        sys.stdout.write("\x07")
        sys.stdout.flush()
    except Exception:
        pass


def enable_mouse() -> None:
    """Enable mouse reporting (SGR extended mode)."""
    try:
        sys.stdout.write(
            "\033[?1000h"  # click events
            "\033[?1002h"  # drag events
            "\033[?1003h"  # any-event tracking
            "\033[?1006h"  # SGR extended mode
        )
        sys.stdout.flush()
    except Exception:
        pass


def disable_mouse() -> None:
    """Disable mouse reporting."""
    try:
        sys.stdout.write(
            "\033[?1000l"
            "\033[?1002l"
            "\033[?1003l"
            "\033[?1006l"
        )
        sys.stdout.flush()
    except Exception:
        pass


def enable_bracketed_paste() -> None:
    """Enable bracketed paste mode."""
    try:
        sys.stdout.write("\033[?2004h")
        sys.stdout.flush()
    except Exception:
        pass


def disable_bracketed_paste() -> None:
    """Disable bracketed paste mode."""
    try:
        sys.stdout.write("\033[?2004l")
        sys.stdout.flush()
    except Exception:
        pass


def enable_synchronized_output() -> None:
    """Begin synchronized output (DEC Private Mode 2026)."""
    try:
        sys.stdout.write("\033[?2026h")
        sys.stdout.flush()
    except Exception:
        pass


def disable_synchronized_output() -> None:
    """End synchronized output."""
    try:
        sys.stdout.write("\033[?2026l")
        sys.stdout.flush()
    except Exception:
        pass
