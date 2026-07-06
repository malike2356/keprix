"""Slash command audit log with secret redaction."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret|authorization|cookie|private[_-]?key)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._-]+"),
    re.compile(r"(?i)kp_[a-z0-9]{8,}"),
    re.compile(r"(?i)sk-[a-z0-9]{8,}"),
]


def redact_args(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact_args(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_args(item) for item in value]
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _audit_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "slash"
    except Exception:
        return Path.home() / ".keprix" / "slash"


class SlashAuditStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._path = (base_dir or _audit_dir()) / "audit.jsonl"

    def write(
        self,
        *,
        workspace_id: str,
        user_id: str,
        channel: str,
        command: str,
        args: dict[str, Any],
        status: str,
        risk_level: str = "low",
        confirmation_required: bool = False,
        confirmation_token_hash: str | None = None,
        error: str | None = None,
    ) -> str:
        audit_id = str(uuid.uuid4())
        row = {
            "id": audit_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "channel": channel,
            "command": command,
            "args_json": redact_args(args),
            "status": status,
            "risk_level": risk_level,
            "confirmation_required": confirmation_required,
            "confirmation_token_hash": confirmation_token_hash,
            "error": error,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat() if status in {"completed", "rejected", "failed"} else None,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        return audit_id

    def list_rows(self, *, workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if workspace_id and row.get("workspace_id") != workspace_id:
                continue
            rows.append(row)
        return rows[-limit:]


_store: SlashAuditStore | None = None


def get_slash_audit_store() -> SlashAuditStore:
    global _store
    if _store is None:
        _store = SlashAuditStore()
    return _store
