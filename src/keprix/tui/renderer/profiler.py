"""Renderer profiling primitives."""

from __future__ import annotations

from dataclasses import dataclass
import time
import tracemalloc


@dataclass(frozen=True)
class RenderProfile:
    elapsed_ms: float
    dirty_rows: int
    rendered_cells: int
    memory_bytes: int


class RenderProfiler:
    def __init__(self) -> None:
        self._start = 0.0
        self._memory_start = 0

    def start(self) -> None:
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        self._start = time.perf_counter()
        self._memory_start = tracemalloc.get_traced_memory()[0]

    def finish(self, *, dirty_rows: int, rendered_cells: int) -> RenderProfile:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        memory_now = tracemalloc.get_traced_memory()[0]
        return RenderProfile(
            elapsed_ms=elapsed_ms,
            dirty_rows=dirty_rows,
            rendered_cells=rendered_cells,
            memory_bytes=max(0, memory_now - self._memory_start),
        )


__all__ = ["RenderProfile", "RenderProfiler"]
