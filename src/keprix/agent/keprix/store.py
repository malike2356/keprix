"""Persistent store for generated tool records."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.schemas import GeneratedToolRecord


def _store_path() -> Path:
    config = get_mutation_config()
    base = Path(config.generated_tools_dir).parent / "mutation"
    base.mkdir(parents=True, exist_ok=True)
    return base / "generated_tools.json"


class GeneratedToolStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _store_path()

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write(self, rows: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def create(
        self,
        *,
        task_that_triggered: str,
        tool_name: str,
        tool_code: str,
        skill_yaml: str,
        description: str,
        gap_description: str,
        static_analysis: dict[str, Any],
        sandbox_result: dict[str, Any],
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GeneratedToolRecord:
        row = {
            "id": str(uuid.uuid4()),
            "task_that_triggered": task_that_triggered,
            "tool_name": tool_name,
            "tool_code": tool_code,
            "skill_yaml": skill_yaml,
            "description": description,
            "gap_description": gap_description,
            "static_analysis": static_analysis,
            "sandbox_result": sandbox_result,
            "status": "pending",
            "approver_id": None,
            "approver_channel": None,
            "rejection_reason": None,
            "approved_at": None,
            "rejected_at": None,
            "installed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "channel_approvals": {},
            "channel_rejections": {},
            "signature": None,
            "session_id": session_id,
            "metadata": metadata or {},
        }
        rows = self._read()
        rows.append(row)
        self._write(rows)
        return self._to_record(row)

    def list_all(self, *, status: str | None = None) -> list[GeneratedToolRecord]:
        rows = self._read()
        if status:
            rows = [row for row in rows if row.get("status") == status]
        return [self._to_record(row) for row in rows]

    def get(self, record_id: str) -> GeneratedToolRecord | None:
        for row in self._read():
            if row["id"] == record_id:
                return self._to_record(row)
        return None

    def update(self, record_id: str, **fields: Any) -> GeneratedToolRecord | None:
        rows = self._read()
        for row in rows:
            if row["id"] == record_id:
                row.update(fields)
                self._write(rows)
                return self._to_record(row)
        return None

    def _to_record(self, row: dict[str, Any]) -> GeneratedToolRecord:
        row.setdefault("channel_approvals", {})
        row.setdefault("channel_rejections", {})
        row.setdefault("signature", None)
        row.setdefault("session_id", None)
        row.setdefault("metadata", {})
        return GeneratedToolRecord(**row)


_store: GeneratedToolStore | None = None


def get_generated_tool_store() -> GeneratedToolStore:
    global _store
    if _store is None:
        _store = GeneratedToolStore()
    return _store
