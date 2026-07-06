"""Per-room configuration store (Prompt 45)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from keprix.backend.messaging.schemas import RoomConfig

CHANNELS_SUPPORTING_ALWAYS_ON = frozenset(
    {"whatsapp", "telegram", "slack", "discord", "matrix", "signal", "webchat"}
)


def _store_dir() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        root = Path(env) / "messaging"
    else:
        try:
            from keprix_cli.config import get_keprix_home

            root = Path(get_keprix_home()) / "messaging"
        except Exception:
            root = Path.home() / ".keprix" / "messaging"
    root.mkdir(parents=True, exist_ok=True)
    return root


class RoomConfigStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _store_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "room_configs.json"
        self._cache: dict[str, RoomConfig] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        for row in payload.get("rooms", []):
            config = RoomConfig.from_dict(row)
            self._cache[self._key(config.workspace_id, config.room_id)] = config

    def _save(self) -> None:
        rows = [config.to_dict() for config in sorted(self._cache.values(), key=lambda row: row.room_id)]
        self._path.write_text(json.dumps({"rooms": rows}, indent=2), encoding="utf-8")

    @staticmethod
    def _key(workspace_id: str, room_id: str) -> str:
        return f"{workspace_id}:{room_id}"

    def get(self, workspace_id: str, room_id: str, *, channel_type: str = "unknown") -> RoomConfig:
        key = self._key(workspace_id, room_id)
        if key not in self._cache:
            self._cache[key] = RoomConfig(room_id=room_id, channel_type=channel_type, workspace_id=workspace_id)
        return self._cache[key]

    def update(self, workspace_id: str, room_id: str, **fields: Any) -> RoomConfig:
        config = self.get(workspace_id, room_id, channel_type=str(fields.pop("channel_type", "unknown")))
        for name, value in fields.items():
            if value is not None and hasattr(config, name):
                setattr(config, name, value)
        self._cache[self._key(workspace_id, room_id)] = config
        self._save()
        return config

    def enable_ambient(self, workspace_id: str, room_id: str, *, channel_type: str = "unknown") -> RoomConfig:
        return self.update(
            workspace_id,
            room_id,
            channel_type=channel_type,
            unmentioned_inbound="room_event",
            visible_replies="message_tool",
        )

    def list_rooms(self, workspace_id: str | None = None) -> list[RoomConfig]:
        rows = list(self._cache.values())
        if workspace_id:
            rows = [row for row in rows if row.workspace_id == workspace_id]
        return sorted(rows, key=lambda row: row.room_id)


_store: RoomConfigStore | None = None


def get_room_config_store() -> RoomConfigStore:
    global _store
    if _store is None:
        _store = RoomConfigStore()
    return _store


def reset_room_config_store(base_dir: Path | None = None) -> RoomConfigStore:
    global _store
    _store = RoomConfigStore(base_dir=base_dir)
    return _store
