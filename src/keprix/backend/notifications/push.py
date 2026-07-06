"""Mobile push notification registration and delivery (Prompt 25)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _push_dir() -> Path:
    import os

    base = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if base:
        root = Path(base) / "notifications" / "push"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "notifications" / "push"
        except Exception:
            root = Path.home() / ".keprix" / "notifications" / "push"
    root.mkdir(parents=True, exist_ok=True)
    return root


class PushTokenStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _push_dir()) / "devices.json"

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def register(
        self,
        *,
        workspace_id: str,
        user_id: str,
        platform: str,
        token: str,
        device_name: str | None = None,
    ) -> dict[str, Any]:
        data = self._load()
        device_id = str(uuid.uuid4())
        row = {
            "id": device_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "platform": platform,
            "token": token,
            "device_name": device_name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        data[device_id] = row
        self._save(data)
        return row

    def list_tokens(self, workspace_id: str, *, user_id: str | None = None) -> list[dict[str, Any]]:
        rows = list(self._load().values())
        rows = [row for row in rows if row.get("workspace_id") == workspace_id]
        if user_id:
            rows = [row for row in rows if row.get("user_id") == user_id]
        return rows


class PushDeliveryService:
    def __init__(self) -> None:
        self._store = PushTokenStore()
        self._sent: list[dict[str, Any]] = []

    def pop_sent(self) -> list[dict[str, Any]]:
        rows = list(self._sent)
        self._sent.clear()
        return rows

    async def send(
        self,
        *,
        workspace_id: str,
        title: str,
        message: str,
        user_id: str | None = None,
        platform: str | None = None,
    ) -> dict[str, Any]:
        tokens = self._store.list_tokens(workspace_id, user_id=user_id)
        if platform:
            tokens = [row for row in tokens if row.get("platform") == platform]
        deliveries = []
        for row in tokens:
            payload = {
                "device_id": row["id"],
                "platform": row.get("platform"),
                "token": row.get("token"),
                "title": title,
                "message": message,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            self._sent.append(payload)
            deliveries.append({"device_id": row["id"], "status": "sent"})
        return {"deliveries": deliveries, "count": len(deliveries)}


_store: PushTokenStore | None = None
_service: PushDeliveryService | None = None


def get_push_token_store() -> PushTokenStore:
    global _store
    if _store is None:
        _store = PushTokenStore()
    return _store


def get_push_service() -> PushDeliveryService:
    global _service
    if _service is None:
        _service = PushDeliveryService()
    return _service


def reset_push_services() -> None:
    global _store, _service
    _store = None
    _service = None
