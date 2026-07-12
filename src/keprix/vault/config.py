"""Universal vault configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from keprix_constants import get_keprix_home


@dataclass
class VaultConfig:
    provider: str = "local_folder"
    root_path: str = ""
    watch: bool = True
    read_only: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _config_path() -> Path:
    path = get_keprix_home() / "config" / "vault.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_config() -> VaultConfig:
    env_root = os.getenv("KEPRIX_VAULT_ROOT")
    if env_root:
        return VaultConfig(root_path=str(Path(env_root).expanduser()))
    path = _config_path()
    if not path.is_file():
        return VaultConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return VaultConfig(**data)


def save_vault_config(config: VaultConfig) -> VaultConfig:
    _config_path().write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config


def get_configured_provider():
    from keprix.vault.local_folder import LocalFolderVault
    from keprix.vault.obsidian_adapter import ObsidianVault

    config = get_vault_config()
    if not config.root_path:
        raise ValueError("Vault root is not configured")
    if config.provider == "obsidian":
        return ObsidianVault(config.root_path)
    return LocalFolderVault(config.root_path)
