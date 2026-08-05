"""Paths for credential proxy state under KEPRIX_HOME."""

from __future__ import annotations

import os
from pathlib import Path


def keprix_home() -> Path:
    raw = os.environ.get("KEPRIX_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".keprix"


def proxy_config_path() -> Path:
    return keprix_home() / "proxy.toml"


def proxy_ca_dir() -> Path:
    return keprix_home() / "proxy-ca"


def proxy_pid_path() -> Path:
    return keprix_home() / "proxy.pid"


def proxy_env_marker_path() -> Path:
    return keprix_home() / ".proxy-env"


def local_vault_path() -> Path:
    return keprix_home() / "proxy-local-vault.json"


def rotation_state_path() -> Path:
    return keprix_home() / "credential-rotation.json"


def rotation_signal_path() -> Path:
    return keprix_home() / "credential-rotation-signal.json"


def migration_state_path() -> Path:
    return keprix_home() / "credential-migration.json"


def fallback_state_path() -> Path:
    return keprix_home() / "credential-fallback.json"
