"""Tests for keprix TUI terminal capabilities detection."""

import os
from unittest.mock import patch

from keprix.tui.terminal_capabilities import (
    TerminalCapabilities,
    detect_terminal_capabilities,
    get_terminal_capabilities,
    terminal_supports_feature,
    force_truecolor,
)


class TestTerminalCapabilities:
    def test_detect_on_modern_terminal(self):
        """Truecolor terminal (Kitty) is detected correctly."""
        with patch.dict(os.environ, {
            "TERM": "xterm-kitty",
            "KITTY_WINDOW_ID": "123",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.terminal_name == "kitty"
            assert caps.truecolor is True
            assert caps.osc52 is True
            assert caps.mouse is True
            assert caps.alternate_screen is True

    def test_detect_wezterm(self):
        """WezTerm is detected correctly."""
        with patch.dict(os.environ, {
            "TERM": "wezterm",
            "WEZTERM_EXECUTABLE": "/usr/bin/wezterm",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.terminal_name == "wezterm"
            assert caps.truecolor is True

    def test_detect_256color_terminal(self):
        """A 256-color terminal without truecolor is detected."""
        with patch.dict(os.environ, {
            "TERM": "xterm-256color",
            "COLORTERM": "",
            "KITTY_WINDOW_ID": "",
            "WEZTERM_EXECUTABLE": "",
            "ITERM_SESSION_ID": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.color_count == 256
            assert caps.truecolor is False

    def test_detect_8color_terminal(self):
        """A basic 8-color terminal."""
        with patch.dict(os.environ, {
            "TERM": "vt100",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.color_count == 8
            assert caps.truecolor is False

    def test_termux_detection(self):
        """Termux is detected on Android."""
        with patch.dict(os.environ, {
            "TERM": "xterm-256color",
            "TERMUX_VERSION": "1.0",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.is_termux is True
            assert caps.alternate_screen is False

    def test_tmux_detection(self):
        """tmux is detected."""
        with patch.dict(os.environ, {
            "TERM": "tmux-256color",
            "TMUX": "/tmp/tmux-1000/default,1234,0",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            caps = detect_terminal_capabilities()
            assert caps.is_tmux is True

    def test_force_truecolor(self):
        """Forcing truecolor sets the env var and clears cache."""
        with patch.dict(os.environ, {"KEPRIX_FORCE_TRUECOLOR": "1", "COLORTERM": "", "TERM": "xterm"}):
            force_truecolor()
            caps = detect_terminal_capabilities()
            assert caps.truecolor is True

    def test_terminal_supports_feature(self):
        """feature check helper works."""
        with patch.dict(os.environ, {
            "TERM": "xterm-kitty",
            "KITTY_WINDOW_ID": "123",
            "COLORTERM": "",
        }):
            get_terminal_capabilities.cache_clear()
            assert terminal_supports_feature("truecolor") is True
            assert terminal_supports_feature("osc52") is True
            assert terminal_supports_feature("nonexistent") is False
