"""Governance connector configuration (file-backed)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _governance_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "governance"
    except Exception:
        root = Path.home() / ".keprix" / "governance"
    root.mkdir(parents=True, exist_ok=True)
    return root


class GovernanceConfig:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _governance_dir()) / "config.json"
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {
            "enabled": os.environ.get("KEPRIX_GOVERNANCE_ENABLED", "").lower() == "true",
            "endpoint": os.environ.get("KEPRIX_GOVERNANCE_ENDPOINT", ""),
            "api_key": os.environ.get("KEPRIX_GOVERNANCE_API_KEY", ""),
            "workspace_id": os.environ.get("KEPRIX_GOVERNANCE_WORKSPACE_ID", ""),
            "audit_stream": False,
            "last_heartbeat": None,
        }

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get(self) -> dict[str, Any]:
        return dict(self._data)

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        allowed = {"enabled", "endpoint", "api_key", "workspace_id", "audit_stream"}
        for key, value in patch.items():
            if key in allowed:
                self._data[key] = value
        self._save()
        return self.get()

    def set_heartbeat(self, status: str) -> None:
        from datetime import datetime, timezone

        self._data["last_heartbeat"] = {
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()


_config: GovernanceConfig | None = None


def get_governance_config() -> GovernanceConfig:
    global _config
    if _config is None:
        _config = GovernanceConfig()
    return _config
