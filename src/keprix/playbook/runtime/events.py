"""Playbook run event stream."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EventType(StrEnum):
    RUN_STARTED = "playbook.run.started"
    NODE_STARTED = "playbook.node.started"
    NODE_COMPLETED = "playbook.node.completed"
    NODE_FAILED = "playbook.node.failed"
    INTERRUPTED = "playbook.interrupted"
    APPROVAL_REQUESTED = "playbook.approval.requested"
    RESUMED = "playbook.resumed"
    COMPLETED = "playbook.completed"
    PAUSED = "playbook.paused"
    CANCELLED = "playbook.cancelled"


@dataclass
class PlaybookEvent:
    event_id: str
    event_type: EventType
    run_id: str
    timestamp: datetime
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
        }


class EventEmitter:
    """In-memory ordered event log for a playbook run."""

    def __init__(self) -> None:
        self._events: list[PlaybookEvent] = []

    def emit(self, event_type: EventType, run_id: str, **payload: Any) -> PlaybookEvent:
        event = PlaybookEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            payload=payload,
        )
        self._events.append(event)
        return event

    def list_events(self, run_id: str | None = None) -> list[PlaybookEvent]:
        if run_id is None:
            return list(self._events)
        return [event for event in self._events if event.run_id == run_id]
