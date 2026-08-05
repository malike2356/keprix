"""Unicode width helpers for terminal layout."""

from __future__ import annotations

import unicodedata


def char_width(char: str) -> int:
    if not char:
        return 0
    category = unicodedata.category(char)
    if category in {"Mn", "Me", "Cf"}:
        return 0
    if unicodedata.east_asian_width(char) in {"W", "F"}:
        return 2
    if ord(char) < 32 or 0x7F <= ord(char) < 0xA0:
        return 0
    return 1


def text_width(text: str) -> int:
    return sum(char_width(ch) for ch in text)

