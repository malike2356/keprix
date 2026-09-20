"""Trajectory event types and dataclass."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

EVENT_TYPES = frozenset(
    {
        "message",
        "tool_call",
        "tool_result",
        "soft_wall",
        "mutation",
        "error",
        "checkpoint",
        "note",
    }
)


@dataclass
class TrajectoryEvent:
    """One append-only event in a session trajectory."""

    event_id: str
    trajectory_id: str
    seq: int
    event_type: str
    timestamp: str
    payload: dict[str, Any] = field(default_factory=dict)
    tool_name: str | None = None
    soft_wall_outcome: str | None = None
    error_text: str | None = None
    parent_trajectory_id: str | None = None
    workspace_id: str = "default"
    session_id: str | None = None
    run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
