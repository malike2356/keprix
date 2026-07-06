"""External notification persistence and rate limiting."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _notify_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "notify_external"
    except Exception:
        root = Path.home() / ".keprix" / "notify_external"
    root.mkdir(parents=True, exist_ok=True)
    return root


def recipient_domain(address: str) -> str:
    if "@" not in address:
        return "unknown"
    return address.rsplit("@", 1)[-1].lower()


class NotifyExternalStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _notify_dir()
        self._config_path = self._dir / "config.json"
        self._notifications_path = self._dir / "notifications.jsonl"
        self._templates_path = self._dir / "custom_templates.json"
        self._hour_counts: dict[str, list[str]] = {}

    def _load_configs(self) -> dict[str, Any]:
        if not self._config_path.exists():
            return {}
        return json.loads(self._config_path.read_text(encoding="utf-8"))

    def get_config(self, workspace_id: str) -> dict[str, Any]:
        configs = self._load_configs()
        row = configs.get(workspace_id, {})
        return {
            "workspace_id": workspace_id,
            "smtp_host": row.get("smtp_host"),
            "smtp_port": int(row.get("smtp_port") or 587),
            "smtp_use_tls": bool(row.get("smtp_use_tls", True)),
            "smtp_username": row.get("smtp_username"),
            "smtp_password_vault_id": row.get("smtp_password_vault_id"),
            "smtp_from_email": row.get("smtp_from_email"),
            "smtp_from_name": row.get("smtp_from_name"),
            "webhook_signing_secret_vault_id": row.get("webhook_signing_secret_vault_id"),
            "max_retries": int(row.get("max_retries") or 3),
            "retry_interval_seconds": int(row.get("retry_interval_seconds") or 300),
        }

    def save_config(self, workspace_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        configs = self._load_configs()
        row = configs.get(workspace_id, {})
        row.update(patch)
        configs[workspace_id] = row
        self._config_path.write_text(json.dumps(configs, indent=2), encoding="utf-8")
        return self.get_config(workspace_id)

    def create_notification(self, workspace_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        row = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "status": "pending",
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        with self._notifications_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return row

    def _read_notifications(self) -> list[dict[str, Any]]:
        if not self._notifications_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._notifications_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write_notifications(self, rows: list[dict[str, Any]]) -> None:
        self._notifications_path.write_text(
            "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

    def get_notification(self, notification_id: str) -> dict[str, Any] | None:
        for row in self._read_notifications():
            if row.get("id") == notification_id:
                return row
        return None

    def update_notification(self, notification_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._read_notifications()
        updated = None
        for index, row in enumerate(rows):
            if row.get("id") != notification_id:
                continue
            row.update(patch)
            rows[index] = row
            updated = row
            break
        if updated is not None:
            self._write_notifications(rows)
        return updated

    def list_notifications(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        channel: str | None = None,
        triggered_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = [
            row
            for row in self._read_notifications()
            if row.get("workspace_id") == workspace_id
            and (status is None or row.get("status") == status)
            and (channel is None or row.get("channel") == channel)
            and (triggered_by is None or row.get("triggered_by") == triggered_by)
        ]
        total = len(rows)
        page = rows[offset : offset + limit]
        return page, total

    def check_rate_limit(self, workspace_id: str, *, limit: int = 100) -> bool:
        now = datetime.now(timezone.utc)
        hour_key = now.strftime("%Y%m%d%H")
        bucket_key = f"{workspace_id}:{hour_key}"
        ids = self._hour_counts.setdefault(bucket_key, [])
        ids = [item for item in ids if item]
        if len(ids) >= limit:
            return False
        ids.append(str(uuid.uuid4()))
        self._hour_counts[bucket_key] = ids
        return True

    def list_custom_templates(self) -> list[dict[str, Any]]:
        if not self._templates_path.exists():
            return []
        return json.loads(self._templates_path.read_text(encoding="utf-8"))

    def save_custom_template(self, template: dict[str, Any]) -> dict[str, Any]:
        rows = self.list_custom_templates()
        rows = [row for row in rows if row.get("name") != template.get("name")]
        rows.append(template)
        self._templates_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return template


_store: NotifyExternalStore | None = None


def get_notify_external_store() -> NotifyExternalStore:
    global _store
    if _store is None:
        _store = NotifyExternalStore()
    return _store


def reset_notify_external_store() -> None:
    global _store
    _store = None
