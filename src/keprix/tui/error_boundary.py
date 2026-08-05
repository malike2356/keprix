"""Error boundary helpers for render-safe TUI work."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import traceback
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class CapturedError:
    message: str
    stack: str


def capture_errors(fn: Callable[[], T]) -> tuple[T | None, CapturedError | None]:
    try:
        return fn(), None
    except Exception as exc:
        return None, CapturedError(message=str(exc), stack=traceback.format_exc())

