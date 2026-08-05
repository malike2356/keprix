"""Mouse event parsing and routing helpers for the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MouseAction(str, Enum):
    PRESS = "press"
    RELEASE = "release"
    DRAG = "drag"
    SCROLL_UP = "scroll_up"
    SCROLL_DOWN = "scroll_down"


@dataclass(frozen=True)
class MouseEvent:
    action: MouseAction
    x: int
    y: int
    button: int = 0
    shift: bool = False
    alt: bool = False
    ctrl: bool = False


def parse_sgr_mouse(sequence: str) -> MouseEvent | None:
    """Parse an SGR mouse sequence such as ``\\x1b[<0;10;5M``."""
    if not sequence.startswith("\x1b[<"):
        return None
    final = sequence[-1:]
    if final not in {"M", "m"}:
        return None
    try:
        raw_button, raw_x, raw_y = sequence[3:-1].split(";")
        code = int(raw_button)
        x = max(0, int(raw_x) - 1)
        y = max(0, int(raw_y) - 1)
    except (TypeError, ValueError):
        return None

    if final == "m":
        action = MouseAction.RELEASE
    elif code & 64:
        action = MouseAction.SCROLL_UP if code & 1 == 0 else MouseAction.SCROLL_DOWN
    elif code & 32:
        action = MouseAction.DRAG
    else:
        action = MouseAction.PRESS

    return MouseEvent(
        action=action,
        x=x,
        y=y,
        button=code & 3,
        shift=bool(code & 4),
        alt=bool(code & 8),
        ctrl=bool(code & 16),
    )

