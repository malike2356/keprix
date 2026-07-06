"""JSONL trajectory logging for coding runs."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.security.redactor import get_redactor


def _trajectory_dir() -> Path:
    base = Path.home() / ".keprix" / "workspace" / "coding-trajectories"
    base.mkdir(parents=True, exist_ok=True)
    return base


@dataclass
class TrajectoryLogger:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: Path | None = None
    _redactor: Any = field(default_factory=get_redactor)

    def __post_init__(self) -> None:
        if self.path is None:
            self.path = _trajectory_dir() / f"{self.run_id}.jsonl"

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run_id": self.run_id,
            "event": event_type,
            "payload": self._redact_payload(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def _redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, str):
                redacted[key] = self._redactor.redact(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_payload(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redactor.redact(item) if isinstance(item, str) else item for item in value
                ]
            else:
                redacted[key] = value
        return redacted

    def read_events(self) -> list[dict[str, Any]]:
        if self.path is None or not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events
