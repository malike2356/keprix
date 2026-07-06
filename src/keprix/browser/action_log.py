"""Browser action log."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _log_dir() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "browser"
    except Exception:
        root = Path.home() / ".keprix" / "browser"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class ActionRecord:
    id: str
    session_id: str
    action: str
    selector: str
    status: str
    created_at: str
    screenshot_id: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ActionLog:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _log_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "actions.json"
        self._rows: list[ActionRecord] = []
        if self._path.exists():
            for row in json.loads(self._path.read_text(encoding="utf-8")):
                self._rows.append(ActionRecord(**row))

    def _save(self) -> None:
        self._path.write_text(
            json.dumps([row.to_dict() for row in self._rows], indent=2),
            encoding="utf-8",
        )

    def append(
        self,
        *,
        session_id: str,
        action: str,
        selector: str = "",
        status: str = "planned",
        screenshot_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActionRecord:
        record = ActionRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            action=action,
            selector=selector,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
            screenshot_id=screenshot_id,
            metadata=metadata or {},
        )
        self._rows.append(record)
        self._save()
        return record

    def list_for_session(self, session_id: str) -> list[ActionRecord]:
        return [row for row in self._rows if row.session_id == session_id]


_log: ActionLog | None = None


def get_action_log() -> ActionLog:
    global _log
    if _log is None:
        _log = ActionLog()
    return _log
