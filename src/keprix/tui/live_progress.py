"""Progress bar rendering helpers."""

from __future__ import annotations


def render_progress(current: int, total: int, *, width: int = 20) -> str:
    total = max(1, total)
    current = max(0, min(current, total))
    filled = round((current / total) * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {current}/{total}"

