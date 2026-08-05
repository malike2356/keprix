from __future__ import annotations

from keprix.tui.renderer.benchmarks import assert_profile_budget, benchmark_transcript_render
from keprix.tui.renderer.snapshots import terminal_degradation_snapshot


def test_10k_transcript_benchmark_has_explicit_budget() -> None:
    lines = [f"message {index} with stable renderer text" for index in range(10_000)]
    profile = benchmark_transcript_render(lines, dirty_rows=0)
    assert profile.rendered_cells > 100_000
    assert profile.dirty_rows == 0
    assert_profile_budget(profile, max_elapsed_ms=250.0, max_memory_bytes=2_000_000)


def test_terminal_degradation_snapshot_is_deterministic() -> None:
    assert terminal_degradation_snapshot(["hello  ", "world"], truecolor=False) == "[basic]\nhello\nworld"
