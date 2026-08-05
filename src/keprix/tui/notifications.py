"""Terminal notification helpers."""

from __future__ import annotations

import sys


def bell(*, enabled: bool = True) -> None:
    if enabled:
        sys.stdout.write("\a")
        sys.stdout.flush()

