"""Persistent clinical event storage (JSONL fallback when audit DB unavailable)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _clinical_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "audit_events"
    except Exception:
        root = Path.home() / ".keprix" / "audit_events"
    root.mkdir(parents=True, exist_ok=True)
    return root


class AuditEventStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _clinical_dir()

    def _path(self, workspace_id: str) -> Path:
        safe = workspace_id.replace("/", "_") or "default"
        return self._dir / f"{safe}.jsonl"

    def append(self, workspace_id: str, event: dict[str, Any]) -> None:
        path = self._path(workspace_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")

    def list_events(
        self,
        workspace_id: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_types: list[str] | None = None,
        domain_pack: str | None = None,
    ) -> list[dict[str, Any]]:
        path = self._path(workspace_id)
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if event_types and row.get("event_type") not in event_types:
                continue
            if domain_pack and row.get("domain_pack") != domain_pack:
                continue
            ts = row.get("timestamp")
            if ts and (date_from or date_to):
                try:
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if date_from and dt < date_from:
                        continue
                    if date_to and dt > date_to:
                        continue
                except ValueError:
                    pass
            rows.append(row)
        return rows


_store: AuditEventStore | None = None


def get_audit_event_store() -> AuditEventStore:
    global _store
    if _store is None:
        _store = AuditEventStore()
    return _store


def reset_audit_event_store() -> None:
    global _store
    _store = None
