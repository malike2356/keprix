"""In-memory crew run events for workspace UI (Prompt 195)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from keprix.teams.crew import Crew


@dataclass
class TeamRunEvent:
    event_type: str
    role: str | None = None
    task_id: str | None = None
    content: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "role": self.role,
            "task_id": self.task_id,
            "content": self.content,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class TeamRunRecord:
    team_name: str
    run_id: str
    status: str = "running"
    state: dict[str, Any] = field(default_factory=dict)
    events: list[TeamRunEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_name": self.team_name,
            "run_id": self.run_id,
            "status": self.status,
            "state": self.state,
            "events": [event.to_dict() for event in self.events],
        }


class TeamRunStore:
    def __init__(self) -> None:
        self._runs: dict[tuple[str, str], TeamRunRecord] = {}

    def create(self, team_name: str, run_id: str | None = None) -> TeamRunRecord:
        rid = run_id or str(uuid4())
        record = TeamRunRecord(team_name=team_name, run_id=rid)
        self._runs[(team_name, rid)] = record
        return record

    def get(self, team_name: str, run_id: str) -> TeamRunRecord | None:
        return self._runs.get((team_name, run_id))

    def append_event(self, team_name: str, run_id: str, event: TeamRunEvent) -> None:
        record = self.get(team_name, run_id)
        if record is None:
            return
        record.events.append(event)

    def finalize(self, team_name: str, run_id: str, *, status: str, state: dict[str, Any]) -> None:
        record = self.get(team_name, run_id)
        if record is None:
            return
        record.status = status
        record.state = dict(state)


team_run_store = TeamRunStore()


def _format_event_content(event_type: str, payload: dict[str, Any]) -> str:
    if event_type == "before_task":
        role = payload.get("role") or "agent"
        task_id = payload.get("task_id") or "task"
        return f"Starting task `{task_id}` as **{role}**."
    if event_type == "after_task":
        result = payload.get("result") or {}
        role = result.get("role") or payload.get("role") or "agent"
        task_id = result.get("task_id") or payload.get("task_id") or "task"
        summary = result.get("output")
        if isinstance(summary, dict):
            text = str(summary.get("summary") or summary.get("objective") or summary)
        else:
            text = str(summary or "Task completed.")
        return f"**{role}** finished `{task_id}`: {text}"
    if event_type == "on_tool_call":
        role = payload.get("role") or "agent"
        task_id = payload.get("task_id") or "tool"
        return f"**{role}** invoked a tool during `{task_id}`."
    if event_type == "on_error":
        return f"Error in `{payload.get('task_id', 'task')}`: {payload.get('error', 'unknown')}"
    if event_type == "on_approval_request":
        return (
            f"Approval required for `{payload.get('task_id')}` "
            f"(risk: {payload.get('risk_level', 'medium')})."
        )
    return event_type.replace("_", " ")


def attach_team_run_recorder(crew: Crew, *, team_name: str, run_id: str) -> None:
    """Subscribe crew hooks to the shared run event store."""
    crew.hooks.events.clear()

    def _record(event_type: str, payload: dict[str, Any]) -> None:
        role = payload.get("role")
        if role is None:
            result = payload.get("result")
            if isinstance(result, dict):
                role = result.get("role")
        team_run_store.append_event(
            team_name,
            run_id,
            TeamRunEvent(
                event_type=event_type,
                role=str(role) if role else None,
                task_id=str(payload.get("task_id")) if payload.get("task_id") else None,
                content=_format_event_content(event_type, payload),
                payload=payload,
            ),
        )

    for event_name in (
        "before_task",
        "after_task",
        "on_tool_call",
        "on_error",
        "on_approval_request",
        "artifact_write",
    ):
        crew.hooks.register(event_name, lambda payload, name=event_name: _record(name, payload))
