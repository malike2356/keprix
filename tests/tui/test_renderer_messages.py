from __future__ import annotations

from datetime import datetime

from keprix.tui.message_types import ToolDisplay, TuiMessage
from keprix.tui.renderer.messages import group_messages, render_message_with_theme, render_tui_message


def test_message_rendering_keeps_role_timestamp_and_metadata() -> None:
    message = TuiMessage(
        role="assistant",
        content="hello https://example.com",
        timestamp=datetime(2026, 7, 13, 12, 0, 0),
        model="mini",
        token_count=12,
        latency_ms=45,
    )
    rendered = render_tui_message(message)
    assert "keprix [12:00:00] (mini | 12 tok | 45 ms)" in rendered
    assert "<https://example.com>" in rendered


def test_tool_cards_and_error_theme_render() -> None:
    tool_message = TuiMessage(role="tool_call", tool=ToolDisplay(name="scan", args={"file": "a.py"}, result="ok"))
    assert "[running] scan file='a.py'" in render_tui_message(tool_message)
    error_message = TuiMessage(role="error", content="failed")
    assert "[red]" in render_message_with_theme(error_message)


def test_role_grouping_keeps_adjacent_messages_together() -> None:
    messages = [
        TuiMessage(role="user", content="one"),
        TuiMessage(role="user", content="two"),
        TuiMessage(role="assistant", content="three"),
    ]
    groups = group_messages(messages)
    assert [group.role for group in groups] == ["user", "assistant"]
    assert groups[0].count == 2
