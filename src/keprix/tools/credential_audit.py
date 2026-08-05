"""Credential use audit trail."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _audit_path() -> Path:
    return Path(os.environ.get("KEPRIX_HOME", Path.home() / ".keprix")).expanduser() / "credential-audit.jsonl"


def record_credential_audit(
    *,
    tool: str,
    route: dict[str, Any],
    credential_ref: str,
    status: str,
    duration_ms: int | float | None = None,
    response_status: int | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "session_id": session_id,
        "route": {
            "host": route.get("host", ""),
            "path": route.get("path", ""),
            "method": route.get("method", ""),
        },
        "credential_ref": credential_ref,
        "status": status,
        "duration_ms": duration_ms,
        "response_status": response_status,
        "rotation_docs_url": "/docs/security/tool-credential-isolation#rotation" if response_status == 401 else None,
    }
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def list_credential_audits(*, limit: int = 100) -> list[dict[str, Any]]:
    path = _audit_path()
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(rows))[:limit]
