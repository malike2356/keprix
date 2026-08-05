"""Upgrade history log: read and write upgrade records to .keprix/upgrade/history.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import UpgradeRecord

_DEFAULT_HISTORY_PATH = Path(".keprix") / "upgrade" / "history.json"


def load_history(history_path: Path | None = None) -> list[UpgradeRecord]:
    """Load upgrade history records from disk. Returns empty list if no history exists."""
    path = history_path or _DEFAULT_HISTORY_PATH
    if not path.exists():
        return []
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        UpgradeRecord(
            from_version=r.get("from", ""),
            to_version=r.get("to", ""),
            timestamp=r.get("timestamp", ""),
            backup_path=r.get("backup_path", ""),
            status=r.get("status", "unknown"),
            duration_seconds=r.get("duration_seconds", 0.0),
        )
        for r in records
    ]


def append_history(record: UpgradeRecord, history_path: Path | None = None) -> None:
    """Append a new upgrade record to the history file."""
    path = history_path or _DEFAULT_HISTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [r.to_dict() for r in load_history(path)]
    records.append(record.to_dict())
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")


def get_last_record(history_path: Path | None = None) -> UpgradeRecord | None:
    """Return the most recent upgrade record, or None if no history exists."""
    records = load_history(history_path)
    return records[-1] if records else None
