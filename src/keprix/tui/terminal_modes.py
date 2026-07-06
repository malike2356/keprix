"""Terminal mode cleanup on TUI exit (Hermes resetTerminalModes port)."""

from __future__ import annotations

import sys


def reset_terminal_modes() -> None:
    """Best-effort restore of mouse and bracketed paste after alt-screen exit."""
    try:
        sys.stdout.write(
            "\033[?1000l"  # mouse click off
            "\033[?1002l"  # mouse drag off
            "\033[?1003l"  # any-event mouse off
            "\033[?1006l"  # SGR mouse off
            "\033[?2004l"  # bracketed paste off
        )
        sys.stdout.flush()
    except Exception:
        pass
