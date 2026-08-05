"""Workspace hot cache configuration."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class HotCacheConfig:
    enabled: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


def config_path(workspace_root: Path) -> Path:
    path = workspace_root / ".keprix" / "hot-cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_hot_cache_config(workspace_root: Path) -> HotCacheConfig:
    path = config_path(workspace_root)
    if not path.is_file():
        return HotCacheConfig(enabled=False)
    return HotCacheConfig(**json.loads(path.read_text(encoding="utf-8")))


def save_hot_cache_config(workspace_root: Path, config: HotCacheConfig) -> HotCacheConfig:
    config_path(workspace_root).write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config
