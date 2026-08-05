from __future__ import annotations

from keprix.tui.renderer.selection import SelectionRange, search_highlights, selected_text_from_lines
from keprix.tui.renderer.viewport import ViewportState, stable_append_viewport, stable_resize_viewport


def test_stable_scroll_on_append_and_resize() -> None:
    viewport = ViewportState(viewport_height=10, content_height=100)
    viewport.scroll_to_bottom()
    stable_append_viewport(viewport, 5)
    assert viewport.visible_range() == (95, 105)
    stable_resize_viewport(viewport, 5, 105)
    assert viewport.visible_range() == (100, 105)


def test_selection_and_search_highlight_work_together() -> None:
    lines = ["alpha beta", "beta gamma", "delta"]
    highlights = search_highlights(lines, "beta")
    assert [(span.line, span.start, span.end) for span in highlights] == [(0, 6, 10), (1, 0, 4)]
    selected = selected_text_from_lines(lines, SelectionRange(start=(0, 6), end=(1, 4)))
    assert selected == "beta\nbeta"
