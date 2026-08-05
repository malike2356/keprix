"""Ponytail ladder mode storage."""

from __future__ import annotations

import json
from dataclasses import dataclass

from keprix_constants import get_keprix_home

LADDER_MODES = {"off", "lite", "full", "ultra"}


@dataclass
class LadderModeConfig:
    mode: str = "full"

    def to_dict(self) -> dict[str, str]:
        return {"mode": self.mode}


def _path():
    path = get_keprix_home() / "config" / "ponytail-ladder.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_ladder_mode() -> LadderModeConfig:
    path = _path()
    if not path.exists():
        return LadderModeConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        mode = str(data.get("mode") or "full")
        return LadderModeConfig(mode=mode if mode in LADDER_MODES else "full")
    except Exception:
        return LadderModeConfig()


def set_ladder_mode(mode: str) -> LadderModeConfig:
    if mode not in LADDER_MODES:
        raise ValueError(f"Unknown ladder mode: {mode}")
    config = LadderModeConfig(mode=mode)
    _path().write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
    return config
