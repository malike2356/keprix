"""Developer API request logs with secret redaction."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.security.redactor import get_redactor


def _logs_file() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        return Path(get_keprix_home()) / "developer" / "api_logs.jsonl"
    except Exception:
        return Path.home() / ".keprix" / "developer" / "api_logs.jsonl"


def redact_request_body(body: str | dict[str, Any] | None) -> str:
    if body is None:
        return ""
    text = body if isinstance(body, str) else json.dumps(body)
    return get_redactor().redact(text)


async def log_request(
    *,
    api_key_id: str | None,
    workspace_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_body: str | dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    entry = {
        "id": str(uuid.uuid4()),
        "api_key_id": api_key_id,
        "workspace_id": workspace_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "request_body_redacted": redact_request_body(request_body),
        "error_message": error_message,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    path_file = _logs_file()
    path_file.parent.mkdir(parents=True, exist_ok=True)
    with path_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def list_logs(workspace_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    path_file = _logs_file()
    if not path_file.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if workspace_id and row.get("workspace_id") != workspace_id:
                continue
            rows.append(row)
    return list(reversed(rows[-limit:]))
