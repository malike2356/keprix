"""Paths for self-configuration artifacts."""

from __future__ import annotations

from pathlib import Path


def get_data_dir() -> Path:
    """Return the directory for self-config state (proposals, overrides, rollback)."""
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "self-config"
    except Exception:
        return Path.home() / ".keprix" / "self-config"


def proposals_file() -> Path:
    return get_data_dir() / "config_proposals.jsonl"


def overrides_env_file() -> Path:
    return get_data_dir() / "overrides.env"


def generated_env_file() -> Path:
    return get_data_dir() / "generated.env"


def rollback_file() -> Path:
    return get_data_dir() / "env_rollback.jsonl"
