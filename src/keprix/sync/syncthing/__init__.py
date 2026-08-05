"""Syncthing bridge for Obsidian vault sync (separate from GitHub agent-sync)."""

from keprix.sync.syncthing.config import has_api_key, load_config, save_api_key, save_config
from keprix.sync.syncthing.service import ensure_vault_folder, get_status, pause_folder, update_settings

__all__ = [
    "ensure_vault_folder",
    "get_status",
    "has_api_key",
    "load_config",
    "pause_folder",
    "save_api_key",
    "save_config",
    "update_settings",
]
