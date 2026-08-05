"""OSC 52 clipboard fallback tests (Prompt 204)."""

from __future__ import annotations

from io import StringIO

from keprix.tui import clipboard as clipboard_mod


def test_osc52_copy_writes_escape_sequence(monkeypatch) -> None:
    buffer = StringIO()
    monkeypatch.setattr(clipboard_mod.sys, "stdout", buffer)
    assert clipboard_mod.osc52_copy("hello") is True
    assert "\033]52;c;" in buffer.getvalue()


def test_copy_text_uses_osc52_when_tools_missing(monkeypatch) -> None:
    buffer = StringIO()
    monkeypatch.setattr(clipboard_mod.shutil, "which", lambda _name: None)
    monkeypatch.setattr(clipboard_mod, "_copy_with_pyperclip", lambda _payload: False)
    monkeypatch.setattr(clipboard_mod.sys, "stdout", buffer)
    assert clipboard_mod.copy_text("ssh copy") is True
    assert "\033]52;c;" in buffer.getvalue()


def test_copy_text_empty_string_is_false() -> None:
    assert clipboard_mod.copy_text("   ") is False
