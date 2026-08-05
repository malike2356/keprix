"""A2A Task Manager: create, track, and finalize multi-step agent tasks."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    STREAMING  = "streaming"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


@dataclass
class TaskArtifact:
    """An output produced by a task step."""
    type: str           # "text" | "json" | "file" | "tool_result"
    content: Any
    step: int = 0
    created_at: float = field(default_factory=time.time)


@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    agent_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    artifacts: list[TaskArtifact] = field(default_factory=list)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_count": len(self.artifacts),
            "error": self.error,
        }


class TaskManager:
    """In-process task registry for A2A workflows.

    Agents create tasks here, poll status, and push artifacts.
    For production deployments, back this with Redis or a DB store.

    Usage::

        mgr = TaskManager()
        task = await mgr.create("Summarise the weekly report")
        await mgr.start(task.id, agent_id="keprix-summariser")
        await mgr.add_artifact(task.id, TaskArtifact(type="text", content="..."))
        await mgr.complete(task.id)
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def create(self, description: str, metadata: dict[str, Any] | None = None) -> Task:
        task = Task(
            id=uuid.uuid4().hex,
            description=description,
            metadata=metadata or {},
        )
        async with self._lock:
            self._tasks[task.id] = task
        return task

    async def start(self, task_id: str, agent_id: str = "") -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.RUNNING
            task.agent_id = agent_id
            task.updated_at = time.time()

    async def mark_streaming(self, task_id: str) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.STREAMING
            task.updated_at = time.time()

    async def complete(self, task_id: str) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.updated_at = time.time()

    async def fail(self, task_id: str, error: str) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error = error
            task.updated_at = time.time()

    async def cancel(self, task_id: str) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.STREAMING):
                task.status = TaskStatus.CANCELLED
                task.updated_at = time.time()

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    async def add_artifact(self, task_id: str, artifact: TaskArtifact) -> None:
        async with self._lock:
            self._tasks[task_id].artifacts.append(artifact)
            self._tasks[task_id].updated_at = time.time()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def list_by_status(self, status: TaskStatus) -> list[Task]:
        async with self._lock:
            return [t for t in self._tasks.values() if t.status == status]

    async def all(self) -> list[Task]:
        async with self._lock:
            return list(self._tasks.values())

    async def purge_completed(self, older_than_seconds: float = 3600) -> int:
        cutoff = time.time() - older_than_seconds
        async with self._lock:
            to_remove = [
                tid for tid, t in self._tasks.items()
                if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
                and t.updated_at < cutoff
            ]
            for tid in to_remove:
                del self._tasks[tid]
        return len(to_remove)
