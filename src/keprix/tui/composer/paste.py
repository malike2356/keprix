"""Paste handling exports."""

from keprix.tui.paste_snip import (
    PASTE_COLLAPSE_THRESHOLD,
    PasteSnipStore,
    collapsed_paste_placeholder,
    line_count,
    should_collapse_paste,
)

__all__ = [
    "PASTE_COLLAPSE_THRESHOLD",
    "PasteSnipStore",
    "collapsed_paste_placeholder",
    "line_count",
    "should_collapse_paste",
]
