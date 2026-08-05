"""Lightweight request tracer: structured spans for multi-step A2A calls."""

from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_id: str
    name: str
    start_time: float
    end_time: float = 0.0
    status: str = "ok"    # "ok" | "error"
    error: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.monotonic()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "status": self.status,
            "error": self.error,
            "attributes": self.attributes,
        }


class Trace:
    """A trace is a collection of spans for one request."""

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.spans: list[Span] = []
        self._lock = asyncio.Lock()

    async def add_span(self, span: Span) -> None:
        async with self._lock:
            self.spans.append(span)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_count": len(self.spans),
            "total_duration_ms": round(
                sum(s.duration_ms for s in self.spans if s.parent_id == ""), 2
            ),
            "spans": [s.to_dict() for s in self.spans],
        }


class Tracer:
    """Create and manage distributed traces for A2A request flows.

    Usage::

        tracer = Tracer()
        async with tracer.start_span("combo.route", trace_id="abc", attributes={"provider": "openai"}) as span:
            ... do work ...
            span.attributes["latency_ms"] = 123.4
    """

    def __init__(self) -> None:
        self._traces: dict[str, Trace] = {}
        self._lock = asyncio.Lock()

    def new_trace_id(self) -> str:
        return uuid.uuid4().hex

    async def get_or_create(self, trace_id: str) -> Trace:
        async with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = Trace(trace_id)
            return self._traces[trace_id]

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        trace_id: str = "",
        parent_id: str = "",
        attributes: dict[str, Any] | None = None,
    ):
        if not trace_id:
            trace_id = self.new_trace_id()
        trace = await self.get_or_create(trace_id)
        span = Span(
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:8],
            parent_id=parent_id,
            name=name,
            start_time=time.monotonic(),
            attributes=attributes or {},
        )
        try:
            yield span
        except Exception as exc:
            span.status = "error"
            span.error = str(exc)
            raise
        finally:
            span.end_time = time.monotonic()
            await trace.add_span(span)

    async def get_trace(self, trace_id: str) -> Trace | None:
        async with self._lock:
            return self._traces.get(trace_id)

    async def purge(self, trace_id: str) -> None:
        async with self._lock:
            self._traces.pop(trace_id, None)
