"""Local TUI preferences stored under KEPRIX_HOME."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.keprix_constants import get_keprix_home

from keprix.api.turn_registry import BUSY_INPUT_MODES, normalize_busy_input_mode
from keprix.tui.theme_system import DEFAULT_THEME_NAME, normalize_theme_name


def _prefs_path() -> Path:
    return get_keprix_home() / "tui.json"


def load_busy_input_override() -> str | None:
    path = _prefs_path()
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    raw = payload.get("busy_input_mode")
    if not isinstance(raw, str):
        return None
    mode = normalize_busy_input_mode(raw)
    return mode if mode in BUSY_INPUT_MODES else None


def _load_preferences() -> dict[str, object]:
    path = _prefs_path()
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                return loaded
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_preferences(existing: dict[str, object]) -> None:
    path = _prefs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def save_busy_input_override(mode: str) -> None:
    normalized = normalize_busy_input_mode(mode)
    existing = _load_preferences()
    existing["busy_input_mode"] = normalized
    _save_preferences(existing)


def load_theme_preference() -> str:
    existing = _load_preferences()
    raw = existing.get("theme")
    if not isinstance(raw, str):
        return DEFAULT_THEME_NAME
    return normalize_theme_name(raw)


def save_theme_preference(theme_name: str) -> str:
    normalized = normalize_theme_name(theme_name)
    existing = _load_preferences()
    existing["theme"] = normalized
    _save_preferences(existing)
    return normalized
