from __future__ import annotations

from keprix.tui.renderer.measure import (
    clamp_text,
    fit_terminal_width,
    iter_grapheme_clusters,
    measure_text,
    strip_terminal_markup,
)


def test_measurement_strips_ansi_and_rich_markup() -> None:
    assert strip_terminal_markup("\x1b[31m[bold]hello[/bold]\x1b[0m") == "hello"
    assert measure_text("\x1b[31m[bold]hello[/bold]\x1b[0m") == 5


def test_measurement_handles_cjk_emoji_zwj_and_combining_marks() -> None:
    assert measure_text("界") == 2
    assert measure_text("e\u0301") == 1
    assert measure_text("👩\u200d💻") == 2
    assert iter_grapheme_clusters("a👩\u200d💻e\u0301") == ["a", "👩\u200d💻", "e\u0301"]


def test_terminal_width_constraints_are_deterministic() -> None:
    assert clamp_text("a界b", 3) == "a界"
    assert fit_terminal_width("abcdef", 5) == "ab..."
