"""Transparency / SGI compliance configuration."""

from __future__ import annotations

import os


def _truthy(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def consent_required() -> bool:
    """When true, AI processing is blocked until granular feature consent exists."""
    return _truthy(os.environ.get("KEPRIX_AI_CONSENT_REQUIRED"), True)


def labeling_enabled() -> bool:
    return _truthy(os.environ.get("KEPRIX_AI_LABELING_ENABLED"), True)


def generation_log_enabled() -> bool:
    return _truthy(os.environ.get("KEPRIX_AI_GENERATION_LOG_ENABLED"), True)
