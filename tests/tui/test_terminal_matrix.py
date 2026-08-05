from __future__ import annotations

from keprix.tui.hardening import terminal_too_small
from keprix.tui.terminal_capabilities import detect_terminal_capabilities


def _caps(monkeypatch, **env):
    for key in ("TERM", "TERM_PROGRAM", "COLORTERM", "TMUX", "TERMUX_VERSION", "KITTY_WINDOW_ID", "WEZTERM_EXECUTABLE", "ITERM_SESSION_ID"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return detect_terminal_capabilities()


def test_terminal_profile_matrix(monkeypatch) -> None:
    assert _caps(monkeypatch, TERM="xterm-256color", COLORTERM="truecolor").truecolor is True
    assert _caps(monkeypatch, TERM="tmux-256color", TMUX="/tmp/tmux").is_tmux is True
    assert _caps(monkeypatch, TERM="screen-256color").is_screen is True
    assert _caps(monkeypatch, TERM="xterm-256color", ITERM_SESSION_ID="1").terminal_name == "iterm2"
    assert _caps(monkeypatch, TERM="xterm-256color", WEZTERM_EXECUTABLE="/usr/bin/wezterm").terminal_name == "wezterm"
    assert _caps(monkeypatch, TERM="xterm-256color", KITTY_WINDOW_ID="1").terminal_name == "kitty"
    assert _caps(monkeypatch, TERM_PROGRAM="Windows Terminal").is_windows_terminal is True
    assert _caps(monkeypatch, TERM_PROGRAM="vscode").is_vscode is True
    assert _caps(monkeypatch, TERMUX_VERSION="1").is_termux is True
    assert _caps(monkeypatch, TERM="dumb").terminal_name == "dumb"


def test_terminal_too_small_detection() -> None:
    assert terminal_too_small(39, 20) is True
    assert terminal_too_small(80, 9) is True
    assert terminal_too_small(80, 24) is False
