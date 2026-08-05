"""Terminal title helpers."""

from __future__ import annotations

import sys


def title_sequence(title: str) -> str:
    safe = title.replace("\x1b", "").replace("\x07", "")
    return f"\x1b]0;{safe}\x07"


def set_terminal_title(title: str) -> None:
    sys.stdout.write(title_sequence(f"keprix; {title}"))
    sys.stdout.flush()

