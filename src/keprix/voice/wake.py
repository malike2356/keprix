"""Gateway-owned wake word registry and routing configuration."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from keprix.voice.bus import broadcast

WAKE_WORD_DEFAULTS = ["keprix", "hey keprix"]
WAKE_WORD_MAX_COUNT = 10
WAKE_WORD_MAX_LENGTH = 40


@dataclass
class WakeWordRoutingConfig:
    version: int = 1
    default_target: dict[str, Any] = field(default_factory=lambda: {"mode": "current"})
    device_targets: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> WakeWordRoutingConfig:
        if not data:
            return cls()
        return cls(
            version=int(data.get("version", 1)),
            default_target=dict(data.get("default_target") or {"mode": "current"}),
            device_targets={
                str(key): dict(value)
                for key, value in (data.get("device_targets") or {}).items()
                if isinstance(value, dict)
            },
        )


def _settings_path(storage_path: Path | None = None) -> Path:
    if storage_path is not None:
        return storage_path
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "settings"
    except ImportError:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "settings"
    return root / "voicewake.json"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def normalize_triggers(triggers: list[str]) -> list[str]:
    normalized = [t.strip().lower() for t in triggers if t and t.strip()]
    normalized = [t for t in normalized if len(t) <= WAKE_WORD_MAX_LENGTH]
    if not normalized:
        return list(WAKE_WORD_DEFAULTS)
    return normalized[:WAKE_WORD_MAX_COUNT]


class WakeWordRegistry:
    """Gateway-owned registry for wake word triggers."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = _settings_path(storage_path)
        self._triggers: list[str] = list(WAKE_WORD_DEFAULTS)
        self._routing = WakeWordRoutingConfig()
        self._updated_at_ms = 0
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._triggers = list(WAKE_WORD_DEFAULTS)
            self._routing = WakeWordRoutingConfig()
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        self._triggers = normalize_triggers(data.get("triggers", WAKE_WORD_DEFAULTS))
        self._routing = WakeWordRoutingConfig.from_dict(data.get("routing"))
        self._updated_at_ms = int(data.get("updated_at_ms", 0))

    def _save(self) -> None:
        self._updated_at_ms = int(time.time() * 1000)
        payload = {
            "triggers": self._triggers,
            "routing": self._routing.to_dict(),
            "updated_at_ms": self._updated_at_ms,
        }
        _atomic_write(self.storage_path, json.dumps(payload, indent=2))

    def get(self) -> list[str]:
        return list(self._triggers)

    def set(self, triggers: list[str]) -> list[str]:
        self._triggers = normalize_triggers(triggers)
        self._save()
        self._emit_updated()
        return list(self._triggers)

    def reset(self) -> list[str]:
        self._triggers = list(WAKE_WORD_DEFAULTS)
        self._save()
        self._emit_updated()
        return list(self._triggers)

    def get_routing(self) -> WakeWordRoutingConfig:
        return WakeWordRoutingConfig.from_dict(self._routing.to_dict())

    def set_routing(self, config: WakeWordRoutingConfig) -> WakeWordRoutingConfig:
        self._routing = WakeWordRoutingConfig.from_dict(config.to_dict())
        self._save()
        self._emit_updated()
        return self.get_routing()

    def snapshot(self) -> dict[str, Any]:
        return {
            "triggers": list(self._triggers),
            "routing": self._routing.to_dict(),
            "updated_at_ms": self._updated_at_ms,
        }

    def _emit_updated(self) -> None:
        broadcast(
            {
                "method": "voicewake.updated",
                "triggers": list(self._triggers),
                "routing": self._routing.to_dict(),
            }
        )
