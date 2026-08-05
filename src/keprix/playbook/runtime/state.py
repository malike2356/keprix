"""Playbook run state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from keprix.compat import StrEnum
from typing import Any


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    FAILED = "failed"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class PlaybookRun:
    run_id: str
    graph_id: str
    workspace_id: str
    status: RunStatus
    state: dict[str, Any] = field(default_factory=dict)
    current_node: str | None = None
    error: str | None = None
    interrupt_reason: str | None = None
    approval_request: dict | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "workspace_id": self.workspace_id,
            "status": self.status.value,
            "state": self.state,
            "current_node": self.current_node,
            "error": self.error,
            "interrupt_reason": self.interrupt_reason,
            "approval_request": self.approval_request,
            "artifacts": self.artifacts,
        }
