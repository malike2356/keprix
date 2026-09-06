"""Durable JSON worker registry with workspace isolation and token hashing."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import uuid
from pathlib import Path
from typing import Any


class WorkerStore:
    def __init__(self, path: Path | None = None) -> None:
        root = Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")) / "workers"
        root.mkdir(parents=True, exist_ok=True)
        self.path = path or root / "workers.json"
        self._lock = threading.RLock()

    def _read(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, rows: list[dict[str, Any]]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def list(self, workspace_id: str) -> list[dict[str, Any]]:
        return [row for row in self._read() if row.get("workspace_id") == workspace_id and not row.get("deleted")]

    def get(self, workspace_id: str, worker_id: str) -> dict[str, Any] | None:
        return next((row for row in self.list(workspace_id) if row.get("id") == worker_id), None)

    def create(self, workspace_id: str, slug: str, persona: str) -> dict[str, Any]:
        with self._lock:
            rows = self._read()
            row = {"id": str(uuid.uuid4()), "workspace_id": workspace_id, "slug": slug.strip().lower(), "persona": persona.strip().upper(), "enabled": True, "preferred": False, "telegram": {}}
            rows.append(row)
            self._write(rows)
            return row

    def update(self, workspace_id: str, worker_id: str, **changes: Any) -> dict[str, Any] | None:
        with self._lock:
            rows = self._read()
            row = next((item for item in rows if item.get("workspace_id") == workspace_id and item.get("id") == worker_id and not item.get("deleted")), None)
            if row is None:
                return None
            row.update(changes)
            self._write(rows)
            return row

    def connect_telegram(self, workspace_id: str, worker_id: str, token: str, chat_id: str) -> dict[str, Any] | None:
        digest = hashlib.sha256((secrets.token_hex(16) + token).encode()).hexdigest()
        return self.update(workspace_id, worker_id, telegram={"token_hash": digest, "chat_id": chat_id, "enabled": True})

    def set_preferred(self, workspace_id: str, worker_id: str) -> dict[str, Any] | None:
        with self._lock:
            rows = self._read()
            target = None
            for row in rows:
                if row.get("workspace_id") != workspace_id or row.get("deleted"):
                    continue
                row["preferred"] = row.get("id") == worker_id
                if row["preferred"]:
                    target = row
            if target is None:
                return None
            self._write(rows)
            return target

    def set_enabled(self, workspace_id: str, worker_id: str, enabled: bool) -> dict[str, Any] | None:
        return self.update(workspace_id, worker_id, enabled=bool(enabled))

    def save_task(self, workspace_id: str, worker_id: str, task: dict[str, Any] | None) -> dict[str, Any] | None:
        return self.update(workspace_id, worker_id, pending_task=task)

    def request_approval(self, workspace_id: str, worker_id: str, action: str, owner_user_id: str) -> dict[str, Any] | None:
        with self._lock:
            rows = self._read()
            row = next((item for item in rows if item.get("workspace_id") == workspace_id and item.get("id") == worker_id and not item.get("deleted")), None)
            if row is None:
                return None
            approval = {"id": str(uuid.uuid4()), "worker_id": worker_id, "worker_slug": row["slug"], "workspace_id": workspace_id, "owner_user_id": owner_user_id, "action": action, "status": "pending"}
            row.setdefault("approvals", []).append(approval)
            self._write(rows)
            return approval


_store: WorkerStore | None = None


def get_worker_store() -> WorkerStore:
    global _store
    if _store is None:
        _store = WorkerStore()
    return _store
