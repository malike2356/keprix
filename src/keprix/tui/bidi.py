"""Basic bidirectional text helpers."""

from __future__ import annotations

import unicodedata


def has_rtl(text: str) -> bool:
    return any(unicodedata.bidirectional(ch) in {"R", "AL", "AN"} for ch in text)


def direction(text: str) -> str:
    return "rtl" if has_rtl(text) else "ltr"

