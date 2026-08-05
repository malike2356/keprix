"""Tests for large paste collapse (Prompt 206)."""

from __future__ import annotations

from keprix.tui.paste_snip import (
    PasteSnipStore,
    collapsed_paste_placeholder,
    line_count,
    should_collapse_paste,
)


def test_should_collapse_paste_threshold() -> None:
    assert should_collapse_paste("x" * 1999) is False
    assert should_collapse_paste("x" * 2000) is True


def test_paste_snip_store_expand() -> None:
    store = PasteSnipStore()
    full = "line one\nline two\n" + ("z" * 2500)
    placeholder = collapsed_paste_placeholder(line_count(full))
    store.store(placeholder, full)
    assert store.expand(placeholder) == full
    assert store.expand("plain text") == "plain text"
