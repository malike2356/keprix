"""Busy input modes supported by the composer."""

BUSY_MODES = ("interrupt", "queue", "steer")


def is_busy_mode(value: str) -> bool:
    return value in BUSY_MODES


__all__ = ["BUSY_MODES", "is_busy_mode"]
