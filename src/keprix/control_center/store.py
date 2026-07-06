"""File-backed control center persistence."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _data_root() -> Path:
    env = os.environ.get("KEPRIX_DATA_DIR", "").strip()
    if env:
        return Path(env)
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home())
    except Exception:
        return Path.home() / ".keprix"


def control_center_home() -> Path:
    path = _data_root() / "control_center"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ControlCenterStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or control_center_home()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._servers_path = self._dir / "servers.json"
        self._sessions_path = self._dir / "sessions.json"
        self._automations_path = self._dir / "automations.json"
        self._queue_path = self._dir / "queue.json"
        self._activity_path = self._dir / "activity.jsonl"
        self._approvals_path = self._dir / "approvals.json"
        self._artifacts_path = self._dir / "artifacts.json"
        self._webhook_secrets_path = self._dir / "webhook_secrets.json"

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_servers(self) -> list[dict[str, Any]]:
        return self._read_json(self._servers_path, [])

    def save_server(self, server: dict[str, Any]) -> dict[str, Any]:
        servers = self.list_servers()
        servers = [item for item in servers if item["id"] != server["id"]]
        servers.append(server)
        self._write_json(self._servers_path, servers)
        return server

    def get_server(self, server_id: str) -> dict[str, Any] | None:
        for server in self.list_servers():
            if server["id"] == server_id:
                return server
        return None

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._read_json(self._sessions_path, [])

    def save_session(self, session: dict[str, Any]) -> dict[str, Any]:
        sessions = self.list_sessions()
        sessions = [item for item in sessions if item["id"] != session["id"]]
        sessions.append(session)
        self._write_json(self._sessions_path, sessions)
        return session

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        for session in self.list_sessions():
            if session["id"] == session_id:
                return session
        return None

    def list_automations(self) -> list[dict[str, Any]]:
        return self._read_json(self._automations_path, [])

    def save_automation(self, automation: dict[str, Any]) -> dict[str, Any]:
        automations = self.list_automations()
        automations = [item for item in automations if item["id"] != automation["id"]]
        automations.append(automation)
        self._write_json(self._automations_path, automations)
        return automation

    def get_automation(self, automation_id: str) -> dict[str, Any] | None:
        for automation in self.list_automations():
            if automation["id"] == automation_id:
                return automation
        return None

    def list_queue(self) -> list[dict[str, Any]]:
        return self._read_json(self._queue_path, [])

    def save_queue_item(self, item: dict[str, Any]) -> dict[str, Any]:
        queue = self.list_queue()
        queue = [row for row in queue if row["id"] != item["id"]]
        queue.append(item)
        self._write_json(self._queue_path, queue)
        return item

    def get_queue_item(self, run_id: str) -> dict[str, Any] | None:
        for item in self.list_queue():
            if item["id"] == run_id:
                return item
        return None

    def append_activity(self, entry: dict[str, Any]) -> dict[str, Any]:
        entry.setdefault("id", str(uuid.uuid4()))
        entry.setdefault("at", _utcnow())
        with self._activity_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        return entry

    def list_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._activity_path.exists():
            return []
        lines = self._activity_path.read_text(encoding="utf-8").strip().splitlines()
        items = [json.loads(line) for line in lines if line.strip()]
        return list(reversed(items[-limit:]))

    def list_approvals(self) -> list[dict[str, Any]]:
        return self._read_json(self._approvals_path, [])

    def save_approval(self, approval: dict[str, Any]) -> dict[str, Any]:
        approvals = self.list_approvals()
        approvals = [item for item in approvals if item["id"] != approval["id"]]
        approvals.append(approval)
        self._write_json(self._approvals_path, approvals)
        return approval

    def list_artifacts(self) -> list[dict[str, Any]]:
        return self._read_json(self._artifacts_path, [])

    def save_artifact(self, artifact: dict[str, Any]) -> dict[str, Any]:
        artifacts = self.list_artifacts()
        artifacts.append(artifact)
        self._write_json(self._artifacts_path, artifacts)
        return artifact

    def set_webhook_secret_ref(self, automation_id: str, vault_id: str) -> None:
        refs = self._read_json(self._webhook_secrets_path, {})
        refs[automation_id] = vault_id
        self._write_json(self._webhook_secrets_path, refs)

    def get_webhook_secret_ref(self, automation_id: str) -> str | None:
        refs = self._read_json(self._webhook_secrets_path, {})
        return refs.get(automation_id)


_store: ControlCenterStore | None = None


def get_control_center_store() -> ControlCenterStore:
    global _store
    if _store is None:
        _store = ControlCenterStore()
    return _store


def reset_control_center_store(store: ControlCenterStore | None = None) -> None:
    global _store
    _store = store
