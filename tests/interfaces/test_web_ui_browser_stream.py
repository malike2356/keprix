"""Stream metadata tests for browser tool progress (Prompt 196)."""

from __future__ import annotations

from keprix.interfaces.web_ui_stream import _browser_tool_stream_mode


def test_browser_tool_stream_mode_for_browser_navigate() -> None:
    assert _browser_tool_stream_mode("browser_navigate") in {"dry_run", "live"}


def test_browser_tool_stream_mode_ignores_other_tools() -> None:
    assert _browser_tool_stream_mode("web_search") is None
