"""Streaming console output for multi-agent runs (Prompt 58)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from datetime import datetime

from keprix.compat import UTC


@dataclass
class StreamEvent:
    run_id: str
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    def sse_line(self) -> str:
        return f"data: {json.dumps(self.to_dict())}\n\n"


class RunStream:
    """Collect and stream run events for operator consoles."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._events: list[StreamEvent] = []

    def emit(self, event_type: str, payload: dict[str, Any] | None = None) -> StreamEvent:
        event = StreamEvent(run_id=self.run_id, event_type=event_type, payload=dict(payload or {}))
        self._events.append(event)
        return event

    def log(self, message: str, *, agent: str = "system") -> StreamEvent:
        return self.emit("console", {"agent": agent, "message": message})

    def events(self) -> list[StreamEvent]:
        return list(self._events)

    async def iter_sse(self) -> AsyncIterator[str]:
        for event in self._events:
            yield event.sse_line()
        yield f"data: {json.dumps({'run_id': self.run_id, 'event_type': 'done'})}\n\n"


_streams: dict[str, RunStream] = {}


def get_run_stream(run_id: str) -> RunStream:
    if run_id not in _streams:
        _streams[run_id] = RunStream(run_id)
    return _streams[run_id]


def clear_streams() -> None:
    _streams.clear()
