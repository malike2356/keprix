"""A2A protocol adapter with shared auth and tracing."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class A2ATask:
    task_id: str
    agent_id: str
    trace_id: str
    input: dict[str, Any]
    status: str = "pending"
    output: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_TASKS: dict[str, A2ATask] = {}


async def handle_a2a(*, agent_id: str, trace_id: str, **payload: Any) -> dict[str, Any]:
    method = payload.get("method", "sendTask")
    if method == "getTask":
        task_id = str(payload.get("task_id", ""))
        task = _TASKS.get(task_id)
        if task is None:
            return {"error": "task not found", "trace_id": trace_id}
        return {"task": _task_to_dict(task), "trace_id": trace_id}
    if method == "cancelTask":
        task_id = str(payload.get("task_id", ""))
        task = _TASKS.get(task_id)
        if task is None:
            return {"error": "task not found", "trace_id": trace_id}
        task.status = "cancelled"
        return {"task": _task_to_dict(task), "trace_id": trace_id}

    task_id = str(payload.get("task_id") or uuid.uuid4())
    task = A2ATask(task_id=task_id, agent_id=agent_id, trace_id=trace_id, input=payload.get("input", {}))
    _TASKS[task_id] = task

    from keprix.interfaces.interface_registry import InterfaceKind, get_interface_registry

    registry = get_interface_registry()
    message = str(task.input.get("message") or task.input.get("text") or "/status")
    result = await registry.dispatch(
        agent_id,
        InterfaceKind.API,
        trace_id=trace_id,
        message=message,
        user_id=payload.get("user_id", "a2a-client"),
        workspace_id=payload.get("workspace_id", "default"),
    )
    task.status = "completed" if result.ok else "failed"
    task.output = result.payload
    return {"task": _task_to_dict(task), "trace_id": trace_id, "interface": "a2a"}


def _task_to_dict(task: A2ATask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "agent_id": task.agent_id,
        "trace_id": task.trace_id,
        "status": task.status,
        "input": task.input,
        "output": task.output,
        "created_at": task.created_at,
    }
