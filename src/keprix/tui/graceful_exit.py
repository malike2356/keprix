"""Graceful exit handler for keprix TUI.

Restores terminal state on exit, saves session data, and handles
cleanup regardless of exit reason (normal quit, signal, crash).
"""

from __future__ import annotations

import atexit
import os
import signal
import sys
from pathlib import Path

from keprix.tui.terminal_modes import reset_terminal_modes

# Path for last-session resume file
LAST_SESSION_PATH = Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")) / "last-tui-session"


def register_exit_handlers(save_last_session_id: str | None = None) -> None:
    """Register cleanup handlers that run on exit."""

    def _on_exit() -> None:
        """Best-effort terminal state restoration."""
        try:
            reset_terminal_modes()
        except Exception:
            pass
        try:
            sys.stdout.write("\033[?25h")  # Show cursor
            sys.stdout.write("\033[?1049l")  # Exit alternate screen
            sys.stdout.flush()
        except Exception:
            pass
        # Save last session ID for resume
        if save_last_session_id:
            _save_last_session(save_last_session_id)

    def _on_signal(signum: int, _frame: object) -> None:
        _on_exit()
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    # Register exit handler
    atexit.register(_on_exit)

    # Handle interrupt signals gracefully
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _on_signal)
        except Exception:
            pass  # Not available in some environments (e.g., threads)

    # SIGPIPE: ignore to prevent crash when output pipe closes
    try:
        signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    except Exception:
        pass


def _save_last_session(session_id: str) -> None:
    """Save the last session ID for resume on next launch."""
    try:
        LAST_SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAST_SESSION_PATH.write_text(session_id)
    except Exception:
        pass


def load_last_session() -> str | None:
    """Load the last session ID for resume. Returns None if not found."""
    try:
        if LAST_SESSION_PATH.exists():
            sid = LAST_SESSION_PATH.read_text().strip()
            if sid:
                return sid
    except Exception:
        pass
    return None


def clear_last_session() -> None:
    """Clear the last session ID."""
    try:
        if LAST_SESSION_PATH.exists():
            LAST_SESSION_PATH.unlink()
    except Exception:
        pass
