"""Raw terminal mode helpers."""

from __future__ import annotations

import sys
import termios
import tty
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def raw_mode(fd: int | None = None) -> Iterator[None]:
    """Temporarily enable raw mode and restore terminal settings on exit."""
    target_fd = sys.stdin.fileno() if fd is None else fd
    try:
        previous = termios.tcgetattr(target_fd)
    except termios.error:
        yield
        return
    try:
        tty.setraw(target_fd)
        yield
    finally:
        termios.tcsetattr(target_fd, termios.TCSADRAIN, previous)

