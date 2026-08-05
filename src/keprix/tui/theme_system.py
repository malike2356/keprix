"""Theme selection and contrast helpers for the Keprix TUI."""

from __future__ import annotations

from keprix.tui.renderer.theme import THEME_NAMES, THEME_TOKENS, ThemeTokens

DEFAULT_THEME_NAME = "Keprix Matrix"


def available_themes() -> tuple[str, ...]:
    return THEME_NAMES


def normalize_theme_name(value: str | None) -> str:
    if not value:
        return DEFAULT_THEME_NAME
    cleaned = " ".join(value.replace("-", " ").replace("_", " ").split()).casefold()
    for name in THEME_NAMES:
        if name.casefold() == cleaned:
            return name
        if name.replace(" ", "").casefold() == cleaned.replace(" ", ""):
            return name
    return DEFAULT_THEME_NAME


def theme_tokens(name: str | None) -> ThemeTokens:
    return THEME_TOKENS[normalize_theme_name(name)]


def theme_class_names() -> tuple[str, ...]:
    return tuple(tokens.class_name for tokens in THEME_TOKENS.values())


def relative_luminance(hex_color: str) -> float:
    raw = hex_color.strip().lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"Expected six digit hex color, got {hex_color!r}")
    channels = [int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def convert(channel: float) -> float:
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = [convert(channel) for channel in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def theme_contrast_report(name: str) -> dict[str, float]:
    tokens = theme_tokens(name)
    pairs = {
        "text": (tokens.text, tokens.background),
        "muted": (tokens.muted, tokens.background),
        "accent": (tokens.accent, tokens.background),
        "selected": (tokens.text, tokens.selected),
        "warning": (tokens.warning, tokens.background),
        "error": (tokens.error, tokens.background),
        "tool": (tokens.tool, tokens.background),
        "timeline": (tokens.timeline, tokens.background),
        "cockpit": (tokens.text, tokens.cockpit),
        "overlay": (tokens.text, tokens.overlay),
    }
    return {key: contrast_ratio(foreground, background) for key, (foreground, background) in pairs.items()}


def theme_passes_contrast(name: str, *, minimum: float = 4.5) -> bool:
    return all(value >= minimum for value in theme_contrast_report(name).values())


__all__ = [
    "DEFAULT_THEME_NAME",
    "available_themes",
    "contrast_ratio",
    "normalize_theme_name",
    "theme_class_names",
    "theme_contrast_report",
    "theme_passes_contrast",
    "theme_tokens",
]
