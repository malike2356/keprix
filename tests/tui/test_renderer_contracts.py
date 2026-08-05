from __future__ import annotations

from datetime import datetime

from keprix.tui.message_types import TuiMessage
from keprix.tui.renderer.code_blocks import extract_code_blocks
from keprix.tui.renderer.diff import diff_frames
from keprix.tui.renderer.markdown import StreamingMarkdownState, find_stable_boundary
from keprix.tui.renderer.measure import clamp_text, measure_text
from keprix.tui.renderer.messages import render_tui_message
from keprix.tui.renderer.snapshots import normalize_snapshot
from keprix.tui.renderer.viewport import ViewportState


def test_measure_handles_unicode_width() -> None:
    assert measure_text("a") == 1
    assert measure_text("界") == 2
    assert clamp_text("a界b", 3) == "a界"


def test_diff_model_compares_frames() -> None:
    diff = diff_frames(["a", "b"], ["a", "c", "d"])
    assert diff.changed
    assert diff.changed_lines == (1, 2)


def test_markdown_renderer_boundary_is_streaming_safe() -> None:
    text = "one\n\n```py\nprint(1)"
    assert find_stable_boundary(text) == 5
    state = StreamingMarkdownState()
    stable, unstable = state.update(text)
    assert stable == "one\n\n"
    assert unstable.startswith("```py")


def test_message_renderer_remains_keprix_themed() -> None:
    rendered = render_tui_message(TuiMessage(role="assistant", content="hello", timestamp=datetime(2026, 7, 13, 12, 0, 0)))
    assert "keprix [12:00:00]" in rendered
    assert "hello" in rendered


def test_viewport_and_snapshots_are_stable() -> None:
    viewport = ViewportState(viewport_height=5, content_height=20)
    viewport.scroll_to_bottom()
    assert viewport.visible_range() == (15, 20)
    assert normalize_snapshot("a  \n\n") == "a"


def test_code_block_extraction() -> None:
    blocks = extract_code_blocks("```python\nprint(1)\n```")
    assert blocks[0].language == "python"
    assert "print" in blocks[0].body
