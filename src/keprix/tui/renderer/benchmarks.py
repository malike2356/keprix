"""CI-friendly renderer benchmark helpers."""

from __future__ import annotations

from keprix.tui.renderer.measure import measure_text
from keprix.tui.renderer.profiler import RenderProfile, RenderProfiler


def benchmark_transcript_render(lines: list[str], *, dirty_rows: int = 0) -> RenderProfile:
    profiler = RenderProfiler()
    profiler.start()
    rendered_cells = sum(measure_text(line) for line in lines)
    return profiler.finish(dirty_rows=dirty_rows, rendered_cells=rendered_cells)


def assert_profile_budget(profile: RenderProfile, *, max_elapsed_ms: float, max_memory_bytes: int) -> None:
    assert profile.elapsed_ms <= max_elapsed_ms
    assert profile.memory_bytes <= max_memory_bytes


__all__ = ["assert_profile_budget", "benchmark_transcript_render"]
