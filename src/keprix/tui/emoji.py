"""Emoji width and sequence helpers."""

from __future__ import annotations

from keprix.tui.unicode_width import text_width

ZWJ = "\u200d"


def is_emoji(char: str) -> bool:
    if not char:
        return False
    code = ord(char[0])
    return 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF


def emoji_width(text: str) -> int:
    if ZWJ in text:
        return 2
    return text_width(text)

