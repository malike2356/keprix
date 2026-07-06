"""Streaming markdown boundary tests."""

from __future__ import annotations

from keprix.tui.streaming_markdown import StreamingMarkdownState, find_stable_boundary


def test_find_stable_boundary_outside_code_fence() -> None:
    text = "Hello\n\nWorld\n\nPartial"
    assert find_stable_boundary(text) == len("Hello\n\nWorld\n\n")


def test_streaming_state_grows_monotonic_prefix() -> None:
    state = StreamingMarkdownState()
    state.update("Line one\n\n")
    stable, tail = state.update("Line one\n\nLine two")
    assert stable == "Line one\n\n"
    assert tail == "Line two"
