"""Cursor advance tracking for keprix TUI.

Tracks cursor position during rendering so the Textual layout engine
can correctly compute line wrapping and cursor placement.  Matches
Hermes's cursor.ts pattern but implemented for Python Textual.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CursorState:
    """Tracks the current cursor position within a rendering context."""

    x: int = 0          # Column (0-based)
    y: int = 0          # Row (0-based)
    max_width: int = 80  # Terminal width for word wrapping

    def advance(self, columns: int = 1) -> None:
        """Advance the cursor by N columns, wrapping if needed."""
        self.x += columns
        while self.x >= self.max_width:
            self.x -= self.max_width
            self.y += 1

    def advance_line(self) -> None:
        """Move to the start of the next line."""
        self.x = 0
        self.y += 1

    def advance_text(self, text: str) -> None:
        """Advance the cursor by the rendered width of a text string."""
        for ch in text:
            if ch == "\n":
                self.advance_line()
            elif ch == "\r":
                self.x = 0
            elif ch == "\t":
                tab_width = 8 - (self.x % 8)
                self.advance(tab_width)
            else:
                w = _char_width(ch)
                self.advance(w)

    def set_position(self, x: int, y: int) -> None:
        """Set absolute cursor position."""
        self.x = x
        self.y = y

    def clone(self) -> CursorState:
        """Return a deep copy of this cursor state."""
        return CursorState(x=self.x, y=self.y, max_width=self.max_width)

    def distance_to(self, other: CursorState) -> int:
        """Calculate the number of lines between two cursor positions."""
        return abs(other.y - self.y)


def _char_width(ch: str) -> int:
    """Return the display width of a single character.

    Returns 1 for normal characters, 2 for CJK/wide characters,
    0 for zero-width characters.
    """
    cp = ord(ch)

    # Zero-width characters
    if cp == 0 or cp in (0x200B, 0x200C, 0x200D, 0xFEFF):  # ZWSP, ZWNJ, ZWJ, BOM
        return 0

    # Combining characters (accents, diacritics)
    if 0x0300 <= cp <= 0x036F:
        return 0
    if 0x1AB0 <= cp <= 0x1AFF:
        return 0
    if 0x1DC0 <= cp <= 0x1DFF:
        return 0
    if 0x20D0 <= cp <= 0x20FF:
        return 0
    if 0xFE20 <= cp <= 0xFE2F:
        return 0

    # Wide characters (CJK, emoji presentation)
    if (
        (0x1100 <= cp <= 0x115F)   # Hangul Jamo
        or (0x2329 <= cp <= 0x232A)  # Misc Technical
        or (0x2E80 <= cp <= 0xA4CF)  # CJK Radicals through Yi
        or (0xA960 <= cp <= 0xA97C)  # Hangul Jamo Extended-A
        or (0xAC00 <= cp <= 0xD7A3)  # Hangul Syllables
        or (0xF900 <= cp <= 0xFAFF)  # CJK Compatibility Ideographs
        or (0xFE10 <= cp <= 0xFE19)  # Vertical Forms
        or (0xFE30 <= cp <= 0xFE6F)  # CJK Compatibility Forms
        or (0xFF01 <= cp <= 0xFF60)  # Fullwidth Forms
        or (0xFFE0 <= cp <= 0xFFE6)  # Fullwidth Signs
        or (0x1F300 <= cp <= 0x1F64F)  # Misc Symbols & Pictographs
        or (0x1F680 <= cp <= 0x1F6FF)  # Transport & Map
        or (0x1F900 <= cp <= 0x1F9FF)  # Supplemental Symbols
        or (0x20000 <= cp <= 0x2FFFD)  # CJK Extension B+
        or (0x30000 <= cp <= 0x3FFFD)  # CJK Extension G+
    ):
        return 2

    # Control characters are non-printing
    if cp < 32 and cp not in (9, 10, 13):  # tab, LF, CR
        return 0

    return 1


def cursor_diff(old: CursorState, new: CursorState) -> str:
    """Generate ANSI escape sequences to move from old to new cursor position."""
    parts = []

    if new.y < old.y or (new.y == old.y and new.x < old.x):
        # Move up
        dy = old.y - new.y
        if dy > 0:
            parts.append(f"\033[{dy}A")
    elif new.y > old.y:
        # Move down
        dy = new.y - old.y
        if dy > 0:
            parts.append(f"\033[{dy}B")

    if new.x != old.x:
        parts.append(f"\033[{new.x + 1}G")

    return "".join(parts)
