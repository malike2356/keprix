"""Notification persistence (Prompt 24)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _notifications_root() -> Path:
    import os

    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "notifications"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "notifications"
        except Exception:
            root = Path.home() / ".keprix" / "notifications"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _workspace_dir(workspace_id: str) -> Path:
    path = _notifications_root() / workspace_id
    path.mkdir(parents=True, exist_ok=True)
    return path


class NotificationStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or _notifications_root()

    def _ws(self, workspace_id: str) -> Path:
        path = self._base / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _append_jsonl(self, path: Path, row: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def _write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.write_text(
            "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

    def create_notification(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self._append_jsonl(self._ws(workspace_id) / "notifications.jsonl", row)
        return row

    def list_notifications(
        self,
        workspace_id: str,
        *,
        user_id: str | None = None,
        unread_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = self._read_jsonl(self._ws(workspace_id) / "notifications.jsonl")
        if user_id:
            rows = [
                row
                for row in rows
                if row.get("user_id") in (None, user_id)
            ]
        if unread_only:
            rows = [row for row in rows if not row.get("read")]
        rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        return rows[offset : offset + limit]

    def get_notification(self, workspace_id: str, notification_id: str) -> dict[str, Any] | None:
        for row in self._read_jsonl(self._ws(workspace_id) / "notifications.jsonl"):
            if row.get("id") == notification_id:
                return row
        return None

    def mark_read(self, workspace_id: str, notification_id: str) -> dict[str, Any] | None:
        path = self._ws(workspace_id) / "notifications.jsonl"
        rows = self._read_jsonl(path)
        updated = None
        for row in rows:
            if row.get("id") == notification_id:
                row["read"] = True
                row["read_at"] = datetime.now(timezone.utc).isoformat()
                updated = row
        if updated:
            self._write_jsonl(path, rows)
        return updated

    def mark_all_read(self, workspace_id: str, user_id: str | None = None) -> int:
        path = self._ws(workspace_id) / "notifications.jsonl"
        rows = self._read_jsonl(path)
        count = 0
        for row in rows:
            if row.get("read"):
                continue
            if user_id and row.get("user_id") not in (None, user_id):
                continue
            row["read"] = True
            row["read_at"] = datetime.now(timezone.utc).isoformat()
            count += 1
        if count:
            self._write_jsonl(path, rows)
        return count

    def unread_count(self, workspace_id: str, user_id: str | None = None) -> int:
        rows = self.list_notifications(workspace_id, user_id=user_id, unread_only=True, limit=100000)
        return len(rows)

    def get_preferences(self, workspace_id: str, user_id: str) -> dict[str, Any]:
        path = self._ws(workspace_id) / "preferences.json"
        if not path.exists():
            return {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "channels_enabled": {
                    "in_app": True,
                    "email": True,
                    "push": True,
                    "slack": False,
                    "telegram": False,
                    "discord": False,
                    "webchat": False,
                },
                "quiet_hours_enabled": False,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "07:00",
                "quiet_hours_timezone": "UTC",
                "digest_enabled": True,
                "escalation_delay_minutes": 60,
            }
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get(user_id) or data.get("default") or {}

    def save_preferences(self, workspace_id: str, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        path = self._ws(workspace_id) / "preferences.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        current = data.get(user_id, self.get_preferences(workspace_id, user_id))
        current.update(patch)
        current["workspace_id"] = workspace_id
        current["user_id"] = user_id
        data[user_id] = current
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return current

    def create_delivery(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "status": "pending",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self._append_jsonl(self._ws(workspace_id) / "deliveries.jsonl", row)
        return row

    def list_deliveries(self, workspace_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = self._read_jsonl(self._ws(workspace_id) / "deliveries.jsonl")
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def update_delivery(self, workspace_id: str, delivery_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        path = self._ws(workspace_id) / "deliveries.jsonl"
        rows = self._read_jsonl(path)
        updated = None
        for row in rows:
            if row.get("id") == delivery_id:
                row.update(patch)
                updated = row
        if updated:
            self._write_jsonl(path, rows)
        return updated

    def create_escalation(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self._append_jsonl(self._ws(workspace_id) / "escalations.jsonl", row)
        return row

    def list_escalations(self, workspace_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        rows = self._read_jsonl(self._ws(workspace_id) / "escalations.jsonl")
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return rows

    def update_escalation(self, workspace_id: str, escalation_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        path = self._ws(workspace_id) / "escalations.jsonl"
        rows = self._read_jsonl(path)
        updated = None
        for row in rows:
            if row.get("id") == escalation_id:
                row.update(patch)
                updated = row
        if updated:
            self._write_jsonl(path, rows)
        return updated

    def queue_digest(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        self._append_jsonl(self._ws(workspace_id) / "digest_queue.jsonl", row)
        return row

    def list_digest_queue(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._read_jsonl(self._ws(workspace_id) / "digest_queue.jsonl")

    def clear_digest_queue(self, workspace_id: str) -> None:
        path = self._ws(workspace_id) / "digest_queue.jsonl"
        if path.exists():
            path.unlink()


_store: NotificationStore | None = None


def get_notification_store() -> NotificationStore:
    global _store
    if _store is None:
        _store = NotificationStore()
    return _store


def reset_notification_store() -> None:
    global _store
    _store = None
