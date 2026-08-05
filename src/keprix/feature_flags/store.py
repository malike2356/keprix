"""File-backed runtime overrides for feature flags."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _flags_path() -> Path:
    try:
        from keprix_constants import get_keprix_home
        root = Path(get_keprix_home())
    except Exception:
        root = Path.home() / ".keprix"
    root.mkdir(parents=True, exist_ok=True)
    return root / "feature_flags.json"


class FeatureFlagStore:
    """Read/write runtime flag overrides from ~/.keprix/feature_flags.json."""

    def load_overrides(self) -> dict[str, bool]:
        path = _flags_path()
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {k: bool(v) for k, v in (data or {}).items()}
        except Exception:
            return {}

    def set(self, flag_id: str, enabled: bool) -> None:
        overrides = self.load_overrides()
        overrides[flag_id] = enabled
        _flags_path().write_text(json.dumps(overrides, indent=2, sort_keys=True), encoding="utf-8")

    def reset(self, flag_id: str) -> None:
        overrides = self.load_overrides()
        overrides.pop(flag_id, None)
        _flags_path().write_text(json.dumps(overrides, indent=2, sort_keys=True), encoding="utf-8")

    def reset_all(self) -> None:
        _flags_path().write_text("{}", encoding="utf-8")

    def resolve(self, runtime_defaults: dict[str, Any]) -> dict[str, bool]:
        """Merge stored overrides on top of runtime defaults (overrides win)."""
        overrides = self.load_overrides()
        merged: dict[str, bool] = {}
        for k, v in runtime_defaults.items():
            merged[k] = bool(v)
        merged.update(overrides)
        return merged
