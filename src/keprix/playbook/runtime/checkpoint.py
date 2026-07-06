"""Checkpoint store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class CheckpointRecord:
    checkpoint_id: str
    run_id: str
    graph_id: str
    node_name: str
    input_state: dict[str, Any]
    output_state: dict[str, Any] | None
    timestamp: datetime
    error: str | None = None
    approval_request: dict | None = None
    artifacts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "graph_id": self.graph_id,
            "node_name": self.node_name,
            "input_state": self.input_state,
            "output_state": self.output_state,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "approval_request": self.approval_request,
            "artifacts": self.artifacts,
        }


class CheckpointStore(ABC):
    @abstractmethod
    async def save(self, record: CheckpointRecord) -> None:
        ...

    @abstractmethod
    async def get_latest(self, run_id: str) -> CheckpointRecord | None:
        ...

    @abstractmethod
    async def list_for_run(self, run_id: str) -> list[CheckpointRecord]:
        ...


def make_checkpoint(
    *,
    run_id: str,
    graph_id: str,
    node_name: str,
    input_state: dict[str, Any],
    output_state: dict[str, Any] | None = None,
    error: str | None = None,
    approval_request: dict | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> CheckpointRecord:
    return CheckpointRecord(
        checkpoint_id=str(uuid4()),
        run_id=run_id,
        graph_id=graph_id,
        node_name=node_name,
        input_state=input_state,
        output_state=output_state,
        timestamp=datetime.now(timezone.utc),
        error=error,
        approval_request=approval_request,
        artifacts=artifacts or [],
    )
