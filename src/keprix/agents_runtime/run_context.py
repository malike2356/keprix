"""Run context and trace event recording."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

TraceEventType = Literal[
    "agent_start",
    "handoff",
    "guardrail",
    "tool",
    "output",
    "agent_end",
    "realtime",
]


@dataclass
class TraceEvent:
    type: TraceEventType
    agent: str
    payload: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "agent": self.agent, "payload": self.payload, "at": self.at}


@dataclass
class RunContext:
    run_id: str
    current_agent: str
    state: dict[str, Any] = field(default_factory=dict)
    trace: list[TraceEvent] = field(default_factory=list)
    accepted_handoffs: list[str] = field(default_factory=list)

    @classmethod
    def start(cls, agent_name: str, *, initial_state: dict[str, Any] | None = None) -> RunContext:
        ctx = cls(run_id=str(uuid.uuid4()), current_agent=agent_name, state=dict(initial_state or {}))
        ctx.record("agent_start", agent_name, {"instructions_agent": agent_name})
        return ctx

    def record(self, event_type: TraceEventType, agent: str, payload: dict[str, Any] | None = None) -> None:
        self.trace.append(TraceEvent(type=event_type, agent=agent, payload=dict(payload or {})))

    def trace_dict(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.trace]


_RUNS: dict[str, RunContext] = {}


def save_run(ctx: RunContext) -> None:
    _RUNS[ctx.run_id] = ctx


def get_run(run_id: str) -> RunContext | None:
    return _RUNS.get(run_id)


def reset_runs() -> None:
    _RUNS.clear()
