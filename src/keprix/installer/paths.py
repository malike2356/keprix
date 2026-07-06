"""Install path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def get_repo_root() -> Path:
    """Repository root (parent of scripts/)."""
    return Path(__file__).resolve().parents[3]


def get_install_root() -> Path:
    """User install directory (default ~/keprix)."""
    raw = os.environ.get("KEPRIX_INSTALL_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "keprix"


def get_env_file() -> Path:
    """Active .env path (repo .env when present, else install root)."""
    explicit = os.environ.get("KEPRIX_ENV_FILE", "").strip()
    if explicit:
        return Path(explicit).expanduser()
    repo_env = get_repo_root() / ".env"
    if repo_env.exists():
        return repo_env
    install_env = get_install_root() / ".env"
    return install_env


def get_state_file() -> Path:
    return get_install_root() / "install-state.json"


def get_backup_dir() -> Path:
    return get_install_root() / "backups"


def get_update_state_file() -> Path:
    return get_install_root() / "update-state.json"
