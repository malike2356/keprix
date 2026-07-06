"""In-memory fallback when Redis is unavailable."""

from __future__ import annotations

import os

_ACTIVE = False


def is_memory_fallback_active() -> bool:
    return _ACTIVE


def activate_memory_fallback() -> None:
    global _ACTIVE
    _ACTIVE = True
    os.environ["KEPRIX_REDIS_MEMORY_FALLBACK"] = "1"


def deactivate_memory_fallback() -> None:
    global _ACTIVE
    _ACTIVE = False
    os.environ.pop("KEPRIX_REDIS_MEMORY_FALLBACK", None)


def reset_memory_fallback() -> None:
    deactivate_memory_fallback()
