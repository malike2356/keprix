"""Typed shapes for durable agent project state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

StepStatus = Literal["pending", "in_progress", "completed", "blocked", "failed"]
ChunkStatus = Literal[
    "pending",
    "in_progress",
    "awaiting_approval",
    "approved",
    "rejected",
    "failed",
    "merged",
]
CheckpointStatus = Literal["none", "awaiting_approval", "approved", "rejected"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class StepRecord:
    id: str
    description: str
    status: StepStatus = "pending"
    output: str | None = None
    chunk_id: str | None = None
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StepRecord:
        return cls(
            id=str(data.get("id") or ""),
            description=str(data.get("description") or ""),
            status=str(data.get("status") or "pending"),  # type: ignore[arg-type]
            output=data.get("output"),
            chunk_id=data.get("chunk_id"),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
        )


@dataclass
class DecisionRecord:
    id: str
    text: str
    at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionRecord:
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            at=str(data.get("at") or utc_now_iso()),
        )


@dataclass
class ConstraintRecord:
    id: str
    text: str
    at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintRecord:
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            at=str(data.get("at") or utc_now_iso()),
        )


@dataclass
class ErrorRecord:
    id: str
    message: str
    step_id: str | None = None
    at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ErrorRecord:
        return cls(
            id=str(data.get("id") or ""),
            message=str(data.get("message") or ""),
            step_id=data.get("step_id"),
            at=str(data.get("at") or utc_now_iso()),
        )


@dataclass
class TaskChunk:
    id: str
    description: str
    steps: list[str]
    dependencies: list[str] = field(default_factory=list)
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    status: ChunkStatus = "pending"
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskChunk:
        return cls(
            id=str(data.get("id") or ""),
            description=str(data.get("description") or ""),
            steps=[str(s) for s in (data.get("steps") or [])],
            dependencies=[str(d) for d in (data.get("dependencies") or [])],
            context_snapshot=dict(data.get("context_snapshot") or {}),
            status=str(data.get("status") or "pending"),  # type: ignore[arg-type]
            summary=data.get("summary"),
        )


@dataclass
class CheckpointGate:
    status: CheckpointStatus = "none"
    chunk_id: str | None = None
    summary: str | None = None
    human_signal: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CheckpointGate:
        data = data or {}
        return cls(
            status=str(data.get("status") or "none"),  # type: ignore[arg-type]
            chunk_id=data.get("chunk_id"),
            summary=data.get("summary"),
            human_signal=data.get("human_signal"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class ProjectState:
    session_id: str
    task_description: str
    version: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    completed: list[StepRecord] = field(default_factory=list)
    in_progress: list[StepRecord] = field(default_factory=list)
    pending: list[StepRecord] = field(default_factory=list)
    blocked: list[StepRecord] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)
    constraints: list[ConstraintRecord] = field(default_factory=list)
    errors: list[ErrorRecord] = field(default_factory=list)
    chunks: list[TaskChunk] = field(default_factory=list)
    current_chunk_id: str | None = None
    checkpoint: CheckpointGate = field(default_factory=CheckpointGate)
    last_completed_step_id: str | None = None
    files_changed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "session_id": self.session_id,
            "task_description": self.task_description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed": [s.to_dict() for s in self.completed],
            "in_progress": [s.to_dict() for s in self.in_progress],
            "pending": [s.to_dict() for s in self.pending],
            "blocked": [s.to_dict() for s in self.blocked],
            "decisions": [d.to_dict() for d in self.decisions],
            "constraints": [c.to_dict() for c in self.constraints],
            "errors": [e.to_dict() for e in self.errors],
            "chunks": [c.to_dict() for c in self.chunks],
            "current_chunk_id": self.current_chunk_id,
            "checkpoint": self.checkpoint.to_dict(),
            "last_completed_step_id": self.last_completed_step_id,
            "files_changed": list(self.files_changed),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        return cls(
            version=int(data.get("version") or 1),
            session_id=str(data.get("session_id") or ""),
            task_description=str(data.get("task_description") or ""),
            created_at=str(data.get("created_at") or utc_now_iso()),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
            completed=[StepRecord.from_dict(s) for s in (data.get("completed") or [])],
            in_progress=[StepRecord.from_dict(s) for s in (data.get("in_progress") or [])],
            pending=[StepRecord.from_dict(s) for s in (data.get("pending") or [])],
            blocked=[StepRecord.from_dict(s) for s in (data.get("blocked") or [])],
            decisions=[DecisionRecord.from_dict(d) for d in (data.get("decisions") or [])],
            constraints=[ConstraintRecord.from_dict(c) for c in (data.get("constraints") or [])],
            errors=[ErrorRecord.from_dict(e) for e in (data.get("errors") or [])],
            chunks=[TaskChunk.from_dict(c) for c in (data.get("chunks") or [])],
            current_chunk_id=data.get("current_chunk_id"),
            checkpoint=CheckpointGate.from_dict(data.get("checkpoint")),
            last_completed_step_id=data.get("last_completed_step_id"),
            files_changed=[str(f) for f in (data.get("files_changed") or [])],
        )

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self.to_dict())

    def all_steps(self) -> list[StepRecord]:
        return [*self.completed, *self.in_progress, *self.pending, *self.blocked]

    def find_step(self, step_id: str) -> StepRecord | None:
        for step in self.all_steps():
            if step.id == step_id:
                return step
        return None

    def next_pending_step(self) -> StepRecord | None:
        if self.in_progress:
            return self.in_progress[0]
        return self.pending[0] if self.pending else None
