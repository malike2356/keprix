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


def _path_tree_usable(path: Path) -> bool:
    """True when path exists and is R/W, or an existing ancestor is writable for mkdir."""
    current = path.expanduser()
    if current.exists():
        return os.access(current, os.R_OK | os.W_OK)
    probe = current
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if not probe.exists():
        return False
    return os.access(probe, os.W_OK)


def coerce_vault_root(root_path: str) -> str:
    """Map host ``~/.keprix/...`` paths onto ``KEPRIX_HOME`` when the host path is unusable.

    Docker bind-mounts host ``~/.keprix`` at ``/home/keprix/.keprix``. Config written on
    the host often stores ``/home/<user>/.keprix/vault``, which is not createable inside
    the container (EACCES on ``/home/<user>``). Remap ``.../.keprix/<tail>`` to
    ``get_keprix_home()/<tail>`` in that case without rewriting vault.json.
    """
    if not root_path:
        return root_path
    raw = Path(root_path).expanduser()
    home = get_keprix_home()
    try:
        home_resolved = home.resolve()
    except OSError:
        home_resolved = home

    parts = raw.parts
    if ".keprix" not in parts:
        return str(raw)

    idx = parts.index(".keprix")
    rel = Path(*parts[idx + 1 :]) if idx + 1 < len(parts) else Path()
    mapped = home_resolved / rel

    if _path_tree_usable(raw):
        try:
            resolved = raw.resolve()
            if resolved == home_resolved or home_resolved in resolved.parents:
                return str(resolved)
            # Host path works (CLI on the same machine); keep it.
            return str(resolved)
        except OSError:
            pass
        return str(raw)

    if _path_tree_usable(mapped) or _path_tree_usable(home_resolved):
        return str(mapped)
    return str(mapped)


def get_vault_config() -> VaultConfig:
    env_root = os.getenv("KEPRIX_VAULT_ROOT")
    if env_root:
        return VaultConfig(root_path=coerce_vault_root(str(Path(env_root).expanduser())))
    path = _config_path()
    if not path.is_file():
        return VaultConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    config = VaultConfig(**data)
    if config.root_path:
        config.root_path = coerce_vault_root(config.root_path)
    return config


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
