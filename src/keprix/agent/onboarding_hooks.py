"""First-message onboarding hooks for HTTP conversation paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def is_first_user_message(history: list[dict[str, Any]] | None) -> bool:
    rows = history or []
    return not any(row.get("role") == "user" for row in rows)


def first_message_system_suffix(*, history: list[dict[str, Any]] | None, config_path: Path | None = None) -> str:
    """Return profile-build directive for the first user message, or empty string."""
    if not is_first_user_message(history):
        return ""

    try:
        from agent.onboarding import (
            PROFILE_BUILD_FLAG,
            is_seen,
            mark_seen,
            profile_build_directive,
            profile_build_mode,
        )
        from keprix_cli.config import get_config_path, load_config
    except Exception:
        return ""

    cfg = load_config()
    if profile_build_mode(cfg) != "ask" or is_seen(cfg, PROFILE_BUILD_FLAG):
        return ""

    path = config_path or get_config_path()
    mark_seen(path, PROFILE_BUILD_FLAG)
    return profile_build_directive()
