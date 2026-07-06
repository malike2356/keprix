"""Collect user feedback and corrections from completed runs."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _feedback_dir() -> Path:
    path = Path.home() / ".keprix" / "workspace" / "improvement" / "feedback"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class FeedbackRecord:
    feedback_id: str
    run_id: str
    agent_id: str
    kind: str
    content: str
    satisfaction: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "kind": self.kind,
            "content": self.content,
            "satisfaction": self.satisfaction,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class FeedbackCollector:
    def record(
        self,
        *,
        run_id: str,
        agent_id: str,
        kind: str,
        content: str,
        satisfaction: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FeedbackRecord:
        record = FeedbackRecord(
            feedback_id=str(uuid.uuid4()),
            run_id=run_id,
            agent_id=agent_id,
            kind=kind,
            content=content,
            satisfaction=satisfaction,
            metadata=metadata or {},
        )
        path = _feedback_dir() / f"{record.feedback_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        return record

    def list_for_run(self, run_id: str) -> list[FeedbackRecord]:
        records: list[FeedbackRecord] = []
        for path in _feedback_dir().glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("run_id") == run_id:
                records.append(FeedbackRecord(**data))
        return records
