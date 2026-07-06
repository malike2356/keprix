"""Speech-to-text configuration helpers for workspace audio routes."""

from __future__ import annotations

from typing import Any


def _load_config() -> dict[str, Any]:
    from keprix_cli.config import load_config

    config = load_config()
    return config if isinstance(config, dict) else {}


def stt_section() -> dict[str, Any]:
    section = _load_config().get("stt")
    return section if isinstance(section, dict) else {}


def stt_enabled() -> bool:
    from tools.transcription_tools import is_stt_enabled

    return is_stt_enabled(stt_section())


def stt_provider() -> str | None:
    if not stt_enabled():
        return None
    return str(stt_section().get("provider") or "local")


def max_recording_seconds() -> int:
    voice = _load_config().get("voice")
    if not isinstance(voice, dict):
        return 120
    try:
        return int(voice.get("max_recording_seconds", 120))
    except (TypeError, ValueError):
        return 120
