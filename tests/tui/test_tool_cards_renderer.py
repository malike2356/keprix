from __future__ import annotations

from keprix.tui.message_renderer import render_message
from keprix.tui.message_types import ToolDisplay, TuiMessage
from keprix.tui.renderer.tool_cards import render_tool_card, tool_card_from_runtime


def test_tool_card_renders_compact_status_args_and_result() -> None:
    card = tool_card_from_runtime(
        name="read_file",
        status="done",
        args={"path": "README.md"},
        result="ok",
        duration_ms=12,
        metadata_id="t1",
    )
    rendered = render_tool_card(card)
    assert "[done] read_file path='README.md' 12 ms #t1" in rendered
    assert "args: path='README.md'" in rendered
    assert "result: ok" in rendered
    assert "state: collapsed" in rendered


def test_message_renderer_uses_inline_tool_card() -> None:
    rendered = render_message(
        TuiMessage(
            role="tool_call",
            tool=ToolDisplay(name="scan", status="running", args={"file": "a.py"}, result="working"),
        )
    )
    assert "[running] scan" in rendered
    assert "args: file='a.py'" in rendered
    assert "result: working" in rendered


def test_failed_tool_card_is_distinct() -> None:
    rendered = render_tool_card(
        tool_card_from_runtime(name="deploy", status="error", error="permission denied")
    )
    assert "[error] deploy" in rendered
    assert "error: permission denied" in rendered
