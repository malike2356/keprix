"""Theme tokens for Keprix TUI rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    class_name: str
    background: str
    surface: str
    panel: str
    border: str
    text: str
    muted: str
    accent: str
    selected: str
    warning: str
    error: str
    success: str
    tool: str
    timeline: str
    cockpit: str
    overlay: str


THEME_TOKENS: dict[str, ThemeTokens] = {
    "Keprix Matrix": ThemeTokens(
        name="Keprix Matrix",
        class_name="theme-keprix-matrix",
        background="#000000",
        surface="#050505",
        panel="#000800",
        border="#003B00",
        text="#00FF41",
        muted="#00A82E",
        accent="#7CFF9B",
        selected="#003B00",
        warning="#F4D35E",
        error="#FF5C5C",
        success="#00FF41",
        tool="#00CC33",
        timeline="#00A82E",
        cockpit="#001A00",
        overlay="#020D05",
    ),
    "Focus Light": ThemeTokens(
        name="Focus Light",
        class_name="theme-focus-light",
        background="#F7F9FB",
        surface="#FFFFFF",
        panel="#EEF3F7",
        border="#A7B4C2",
        text="#17202A",
        muted="#415466",
        accent="#005FCC",
        selected="#D7E8FF",
        warning="#8A5A00",
        error="#B42318",
        success="#146C43",
        tool="#0B5CAD",
        timeline="#334E68",
        cockpit="#E8F1FA",
        overlay="#FFFFFF",
    ),
    "Operator Dark": ThemeTokens(
        name="Operator Dark",
        class_name="theme-operator-dark",
        background="#101418",
        surface="#161C22",
        panel="#1E262E",
        border="#47515C",
        text="#E7EEF6",
        muted="#A9B6C3",
        accent="#62D0FF",
        selected="#26384A",
        warning="#FFD166",
        error="#FF6B6B",
        success="#7BD88F",
        tool="#9CDCFE",
        timeline="#B8C7D9",
        cockpit="#18222D",
        overlay="#121820",
    ),
}

KEPRIX_THEME_TOKENS = {
    "accent": "cyan",
    "warning": THEME_TOKENS["Keprix Matrix"].warning,
    "error": "red",
    "muted": THEME_TOKENS["Keprix Matrix"].muted,
}

THEME_NAMES = tuple(THEME_TOKENS.keys())

__all__ = ["KEPRIX_THEME_TOKENS", "THEME_NAMES", "THEME_TOKENS", "ThemeTokens"]
