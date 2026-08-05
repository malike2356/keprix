"""Durable JSON store for public /v1/tasks."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path() -> Path:
    try:
        from keprix.auth.config import data_dir

        root = Path(data_dir()) / "public_api"
    except Exception:
        root = Path.home() / ".keprix" / "public_api"
    root.mkdir(parents=True, exist_ok=True)
    return root / "tasks.json"


class PublicTaskStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _path()
        self._lock = threading.RLock()
        self._tasks: dict[str, dict[str, Any]] = {}
        if self._path.exists():
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            self._tasks = {str(t["id"]): t for t in (payload.get("tasks") or [])}

    def _save(self) -> None:
        self._path.write_text(
            json.dumps({"tasks": list(self._tasks.values())}, indent=2),
            encoding="utf-8",
        )

    def create(self, *, workspace_id: str, title: str) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "title": title.strip(),
            "status": "open",
            "user": workspace_id,
            "workspace_id": workspace_id,
            "created_at": _utcnow(),
            "updated_at": _utcnow(),
        }
        with self._lock:
            self._tasks[row["id"]] = row
            self._save()
        return dict(row)

    def list_for_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = [t for t in self._tasks.values() if t.get("workspace_id") == workspace_id]
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return [dict(r) for r in rows]


_store: PublicTaskStore | None = None


def get_public_task_store() -> PublicTaskStore:
    global _store
    if _store is None:
        _store = PublicTaskStore()
    return _store
