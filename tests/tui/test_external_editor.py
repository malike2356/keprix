"""Tests for external editor compose (Prompt 206)."""

from __future__ import annotations

from keprix.tui.external_editor import edit_in_editor, resolve_editor


def test_resolve_editor_prefers_explicit(monkeypatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    assert resolve_editor("/usr/bin/nano") == "/usr/bin/nano"


def test_resolve_editor_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("EDITOR", "vim")
    assert resolve_editor() == "vim"


def test_edit_in_editor_missing_editor(monkeypatch) -> None:
    monkeypatch.delenv("EDITOR", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    assert edit_in_editor("hello") is None


def test_edit_in_editor_returns_trimmed_text(monkeypatch, tmp_path) -> None:
    script = tmp_path / "fake-editor.sh"
    script.write_text(
        "#!/bin/sh\n"
        'printf "\\nedited line\\n" >> "$1"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setenv("EDITOR", str(script))
    result = edit_in_editor("seed")
    assert result == "seed\nedited line"
