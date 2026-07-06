"""Migration history persistence (Prompt 42)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _history_dir() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        root = Path(env) / "migration"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "migration"
        except Exception:
            root = Path.home() / ".keprix" / "migration"
    root.mkdir(parents=True, exist_ok=True)
    return root


class MigrationHistoryStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _history_dir()
        self._path = self._dir / "history.jsonl"
        self._skills_dir = self._dir / "skills"
        self._skills_dir.mkdir(parents=True, exist_ok=True)

    def record(self, row: dict[str, Any]) -> dict[str, Any]:
        payload = {
            **row,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        return payload

    def list_history(self, workspace_id: str | None = None) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows = [
            json.loads(line)
            for line in self._path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if workspace_id:
            rows = [row for row in rows if row.get("workspace_id") == workspace_id]
        return sorted(rows, key=lambda row: row.get("recorded_at", ""), reverse=True)

    def save_skill(self, workspace_id: str, skill: dict[str, Any]) -> dict[str, Any]:
        path = self._skills_dir / f"{workspace_id}.json"
        existing: list[dict[str, Any]] = []
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        existing.append(skill)
        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        return skill


_store: MigrationHistoryStore | None = None


def get_migration_history_store() -> MigrationHistoryStore:
    global _store
    if _store is None:
        _store = MigrationHistoryStore()
    return _store


def reset_migration_history_store(base_dir: Path | None = None) -> MigrationHistoryStore:
    global _store
    _store = MigrationHistoryStore(base_dir=base_dir)
    return _store
