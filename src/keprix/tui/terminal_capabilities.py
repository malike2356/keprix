"""Terminal capability detection for keprix TUI.

Probes the terminal on startup for available features, caches results,
and provides graceful degradation for unsupported terminals.

Supports: truecolor detection, OSC 52 clipboard, mouse support,
alternate screen, bracketed paste, synchronized output, kitty keyboard
protocol, and terminal emulator identification.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class TerminalCapabilities:
    """Detected terminal capabilities at startup."""

    # Color
    truecolor: bool = False
    color_count: int = 8  # 8, 16, 256, or 16777216

    # Clipboard
    osc52: bool = False

    # Input
    mouse: bool = False
    bracketed_paste: bool = False
    kitty_keyboard: bool = False

    # Display
    alternate_screen: bool = False
    synchronized_output: bool = False

    # Terminal identity
    terminal_name: str = "unknown"
    is_tmux: bool = False
    is_screen: bool = False
    is_termux: bool = False
    is_vscode: bool = False
    is_windows_terminal: bool = False

    # Limits
    max_colors: int = 8

    # Feature flags detected but not probed
    _probed: bool = field(default=False, repr=False)


def detect_terminal_capabilities() -> TerminalCapabilities:
    """Probe the terminal for available features and cache results."""
    caps = TerminalCapabilities()
    _probe_terminal_identity(caps)
    _probe_color(caps)
    _probe_osc52(caps)
    _probe_mouse(caps)
    _probe_alternate_screen(caps)
    caps._probed = True
    return caps


@lru_cache(maxsize=1)
def get_terminal_capabilities() -> TerminalCapabilities:
    """Return cached terminal capabilities. Probes on first call."""
    return detect_terminal_capabilities()


def _probe_terminal_identity(caps: TerminalCapabilities) -> None:
    """Identify the terminal emulator from environment variables."""
    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    term_program_version = os.environ.get("TERM_PROGRAM_VERSION", "")
    colorterm = os.environ.get("COLORTERM", "").lower()

    caps.terminal_name = term or "unknown"
    caps.is_tmux = "tmux" in term or bool(os.environ.get("TMUX"))
    caps.is_screen = term.startswith("screen")
    caps.is_termux = bool(os.environ.get("TERMUX_VERSION"))
    caps.is_vscode = term_program == "vscode"
    caps.is_windows_terminal = "windows terminal" in term_program

    # Detect specific terminal emulators
    if "kitty" in term or os.environ.get("KITTY_WINDOW_ID"):
        caps.terminal_name = "kitty"
    elif os.environ.get("WEZTERM_EXECUTABLE"):
        caps.terminal_name = "wezterm"
    elif os.environ.get("ITERM_SESSION_ID"):
        caps.terminal_name = "iterm2"
    elif os.environ.get("ALACRITTY_LOG"):
        caps.terminal_name = "alacritty"
    elif term == "foot":
        caps.terminal_name = "foot"
    elif caps.is_windows_terminal:
        caps.terminal_name = "windows-terminal"


def _probe_color(caps: TerminalCapabilities) -> None:
    """Detect color capabilities."""
    colorterm = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "").lower()

    # 24-bit truecolor terminals
    if colorterm in ("truecolor", "24bit"):
        caps.truecolor = True
        caps.color_count = 1 << 24
        caps.max_colors = 1 << 24
        return

    # Terminals known to support truecolor
    truecolor_terms = (
        "kitty", "wezterm", "foot", "alacritty",
        "iterm2", "windows-terminal", "rio", "warp",
    )
    if caps.terminal_name in truecolor_terms:
        caps.truecolor = True
        caps.color_count = 1 << 24
        caps.max_colors = 1 << 24
        return

    # Check for tmux with truecolor support
    if caps.is_tmux:
        if "tmux-256color" in term or "-256color" in term:
            caps.color_count = 256
            caps.max_colors = 256
            return

    # 256-color terminals
    if "256color" in term or "256" in colorterm:
        caps.color_count = 256
        caps.max_colors = 256
        return

    # 16-color terminals
    if term.endswith("color") or "16color" in term:
        caps.color_count = 16
        caps.max_colors = 16
        return

    # Fallback: 8 colors
    caps.color_count = 8
    caps.max_colors = 8


def _probe_osc52(caps: TerminalCapabilities) -> None:
    """Check if OSC 52 clipboard sequences are supported."""
    # Terminals known to support OSC 52
    osc52_terminals = ("kitty", "wezterm", "foot", "iterm2", "alacritty")
    if caps.terminal_name in osc52_terminals:
        caps.osc52 = True
        return

    # Check if explicitly enabled
    if os.environ.get("OSC52", "").lower() in ("1", "true", "yes"):
        caps.osc52 = True
        return

    # tmux with allow-passthrough
    if caps.is_tmux and os.environ.get("TMUX_ALLOW_PASSTHROUGH"):
        caps.osc52 = True
        return


def _probe_mouse(caps: TerminalCapabilities) -> None:
    """Check if mouse is available."""
    # Most modern terminals support mouse
    term = os.environ.get("TERM", "").lower()
    if "xterm" in term or "256color" in term:
        caps.mouse = True


def _probe_alternate_screen(caps: TerminalCapabilities) -> None:
    """Check if alternate screen is supported."""
    # Termux doesn't have alternate screen
    if caps.is_termux:
        caps.alternate_screen = False
        return
    # tmux/screen have their own alternate screen handling
    if caps.is_tmux or caps.is_screen:
        caps.alternate_screen = True
        return
    # Most terminals support it
    caps.alternate_screen = True


def force_truecolor() -> None:
    """Force the terminal into truecolor mode via env var."""
    os.environ["COLORTERM"] = "truecolor"
    get_terminal_capabilities.cache_clear()


def is_force_truecolor_set() -> bool:
    """Check if KEPRIX_FORCE_TRUECOLOR env var is set."""
    return os.environ.get("KEPRIX_FORCE_TRUECOLOR", "").lower() in ("1", "true", "yes")


def terminal_supports_feature(feature: str) -> bool:
    """Check if the terminal supports a named feature.

    Features: 'truecolor', 'osc52', 'mouse', 'alternate_screen',
              'bracketed_paste', 'kitty_keyboard'
    """
    caps = get_terminal_capabilities()
    return bool(getattr(caps, feature, False))
