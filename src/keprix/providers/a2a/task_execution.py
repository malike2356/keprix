"""A2A Task Executor: run a task through the combo engine with artifact capture."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable

from .task_manager import Task, TaskArtifact, TaskManager, TaskStatus

logger = logging.getLogger(__name__)

# Streaming chunk type
StreamChunk = dict[str, Any]

# Type for a streaming LLM call: (messages) -> async iterator of chunks
StreamCallFn = Callable[[list[dict]], "AsyncIterator[StreamChunk]"]


@dataclass
class ExecutionResult:
    task_id: str
    success: bool
    output: str = ""
    artifacts: list[TaskArtifact] = field(default_factory=list)
    error: str = ""
    duration_ms: float = 0.0
    token_usage: dict[str, int] = field(default_factory=dict)


class TaskExecutor:
    """Execute agent tasks with streaming support and artifact capture.

    Usage (non-streaming)::

        executor = TaskExecutor(task_manager)
        result = await executor.run(task, messages, call_fn)

    Usage (streaming)::

        async for chunk in executor.stream(task, messages, stream_fn):
            yield chunk  # forward SSE chunks to client
    """

    def __init__(self, manager: TaskManager) -> None:
        self._mgr = manager

    async def run(
        self,
        task: Task,
        messages: list[dict[str, Any]],
        call_fn: Callable[..., Awaitable[Any]],
        agent_id: str = "",
        **call_kwargs: Any,
    ) -> ExecutionResult:
        """Execute a task with a single (non-streaming) LLM call."""
        t0 = time.perf_counter()
        await self._mgr.start(task.id, agent_id=agent_id)

        try:
            response = await call_fn(messages, **call_kwargs)
            duration_ms = (time.perf_counter() - t0) * 1000

            content = self._extract_content(response)
            token_usage = self._extract_usage(response)

            artifact = TaskArtifact(type="text", content=content, step=1)
            await self._mgr.add_artifact(task.id, artifact)
            await self._mgr.complete(task.id)

            return ExecutionResult(
                task_id=task.id,
                success=True,
                output=content,
                artifacts=[artifact],
                duration_ms=duration_ms,
                token_usage=token_usage,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            error = str(exc)
            await self._mgr.fail(task.id, error)
            logger.error("Task %s failed: %s", task.id, error)
            return ExecutionResult(
                task_id=task.id,
                success=False,
                error=error,
                duration_ms=duration_ms,
            )

    async def stream(
        self,
        task: Task,
        messages: list[dict[str, Any]],
        stream_fn: StreamCallFn,
        agent_id: str = "",
    ) -> AsyncIterator[StreamChunk]:
        """Execute a task with streaming, yielding chunks as they arrive."""
        await self._mgr.start(task.id, agent_id=agent_id)
        await self._mgr.mark_streaming(task.id)
        t0 = time.perf_counter()
        collected: list[str] = []

        try:
            async for chunk in stream_fn(messages):
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if delta:
                    collected.append(delta)
                chunk["_task_id"] = task.id
                yield chunk

            full_content = "".join(collected)
            artifact = TaskArtifact(type="text", content=full_content, step=1)
            await self._mgr.add_artifact(task.id, artifact)
            await self._mgr.complete(task.id)

            duration_ms = (time.perf_counter() - t0) * 1000
            yield {
                "_done": True,
                "_task_id": task.id,
                "_duration_ms": round(duration_ms, 1),
            }
        except Exception as exc:
            error = str(exc)
            await self._mgr.fail(task.id, error)
            logger.error("Streaming task %s failed: %s", task.id, error)
            yield {"_error": error, "_task_id": task.id}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content(response: Any) -> str:
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return str(response.get("content", ""))
        return str(response)

    @staticmethod
    def _extract_usage(response: Any) -> dict[str, int]:
        if isinstance(response, dict):
            return response.get("usage", {})
        return {}
