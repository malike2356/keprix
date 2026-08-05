"""Coding preflight configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
from typing import Any

import yaml

from keprix_constants import get_keprix_home


@dataclass
class PreflightConfig:
    enabled: bool = True
    diff_budget_lines: int = 400
    duplicate_window_turns: int = 8
    provider_budget_warn_pct: int = 85
    allow_override: bool = True
    gates: dict[str, bool] = field(
        default_factory=lambda: {
            "repo_index": True,
            "duplicate_task": True,
            "test_exists": True,
            "diff_budget": True,
            "provider_budget": True,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_preflight_config() -> PreflightConfig:
    enabled_env = os.getenv("KEPRIX_CODING_PREFLIGHT")
    config = PreflightConfig(enabled=enabled_env.lower() not in {"0", "false", "no"} if enabled_env is not None else True)
    path = get_keprix_home() / "config.yaml"
    if not path.is_file():
        return config
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return config
    section = raw.get("coding_preflight")
    if not isinstance(section, dict):
        return config
    for key in ("enabled", "diff_budget_lines", "duplicate_window_turns", "provider_budget_warn_pct", "allow_override"):
        if key in section:
            setattr(config, key, section[key])
    if isinstance(section.get("gates"), dict):
        config.gates.update({str(key): bool(value) for key, value in section["gates"].items()})
    return config


def save_preflight_config(config: PreflightConfig) -> PreflightConfig:
    path = get_keprix_home() / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw: dict[str, Any] = {}
    if path.is_file():
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            raw = {}
    raw["coding_preflight"] = config.to_dict()
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return config
