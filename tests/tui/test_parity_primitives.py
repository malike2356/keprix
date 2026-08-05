from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from keprix.tui.composer import InputHistory
from keprix.tui.fuzzy_match import fuzzy_filter
from keprix.tui.gateway_handler import GatewayMessageRouter
from keprix.tui.history_search import search_history
from keprix.tui.hit_test import HitMap, Point, Region
from keprix.tui.input_metrics import measure_input
from keprix.tui.live_progress import render_progress
from keprix.tui.message_renderer import collapse_duplicates, render_message
from keprix.tui.message_types import ToolDisplay, TuiMessage
from keprix.tui.mouse import MouseAction, parse_sgr_mouse
from keprix.tui.render_budget import RenderBudget
from keprix.tui.slash_arg_parser import parse_slash_args
from keprix.tui.terminal_title import title_sequence
from keprix.tui.unicode_width import text_width
from keprix.tui.virtual_history import InMemoryHistorySource, VirtualHistory
from keprix.tui.virtual_renderer import render_visible
from keprix.tui.widgets.app_layout import AppLayoutState
from keprix.tui.widgets.skills_hub import SkillItem, SkillsHubState
from keprix.tui.widgets.todo_panel import TodoPanelState


def test_mouse_sgr_parse_scroll_and_press() -> None:
    press = parse_sgr_mouse("\x1b[<0;10;5M")
    assert press is not None
    assert press.action == MouseAction.PRESS
    assert (press.x, press.y) == (9, 4)

    scroll = parse_sgr_mouse("\x1b[<65;3;4M")
    assert scroll is not None
    assert scroll.action == MouseAction.SCROLL_DOWN


def test_hit_map_returns_topmost_region() -> None:
    hit_map = HitMap()
    hit_map.add(Region(0, 0, 10, 10, "base"))
    hit_map.add(Region(2, 2, 3, 3, "top"))
    assert hit_map.hit(Point(3, 3)).id == "top"
    assert hit_map.hit(Point(11, 3)) is None


def test_message_renderer_metadata_tool_links_and_duplicates() -> None:
    msg = TuiMessage(
        role="tool_call",
        content="See https://example.com and ./README.md",
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        model="mini",
        token_count=12,
        latency_ms=34,
        tool=ToolDisplay(name="read_file", status="done", args={"path": "README.md"}, result="ok"),
    )
    rendered = render_message(msg)
    assert "tool [12:00:00] (mini | 12 tok | 34 ms)" in rendered
    assert "[done] read_file path='README.md'" in rendered
    assert "<https://example.com>" in rendered
    assert "[file:README.md]" in rendered
    assert collapse_duplicates(["same", "same"]) == ["same\n[2 duplicates]"]


def test_virtual_history_search_and_rendering() -> None:
    messages = [TuiMessage(role="user", content=f"message {idx}") for idx in range(20)]
    history = VirtualHistory(InMemoryHistorySource(messages), page_size=5)
    window = history.window("s1", anchor=10, visible_count=5)
    assert window.offset == 10
    assert len(window.messages) == 5
    assert search_history(messages, "message 12")[0].index == 12
    assert len(render_visible(messages, scroll_offset=18, viewport_height=10)) == 2


def test_input_history_persists_ten_thousand_items(tmp_path: Path) -> None:
    path = tmp_path / "history.txt"
    history = InputHistory(max_items=10_000, path=path)
    for idx in range(10_005):
        history.push(f"item {idx}")
    loaded = InputHistory(max_items=10_000, path=path)
    snapshot = loaded.snapshot()
    assert len(snapshot) == 10_000
    assert snapshot[0] == "item 5"
    assert snapshot[-1] == "item 10004"


def test_fuzzy_slash_args_metrics_progress_and_width() -> None:
    assert fuzzy_filter("mdl", ["/model", "/memory", "/clear"])[0] == "/model"
    parsed = parse_slash_args('/config set model "gpt mini" --global --tries=2')
    assert parsed.command == "/config"
    assert parsed.positional == ["set", "model", "gpt mini"]
    assert parsed.flags == {"global": True, "tries": "2"}
    assert measure_input("hello world").words == 2
    assert render_progress(5, 10, width=10) == "[#####-----] 5/10"
    assert text_width("A") == 1
    assert text_width("界") == 2


def test_terminal_title_budget_and_widgets() -> None:
    assert title_sequence("hello") == "\x1b]0;hello\x07"
    assert RenderBudget(target_fps=50).over_budget(25)
    assert AppLayoutState(left_collapsed=True).effective_widths(100)[0] == 0
    todos = TodoPanelState()
    todos.add("1", "Ship parity")
    assert todos.toggle("1") is True
    assert "[x] Ship parity" in todos.render()
    skills = SkillsHubState([SkillItem(name="researcher", description="Search")])
    assert skills.search("search")[0].name == "researcher"


def test_gateway_router_dispatches_typed_messages() -> None:
    seen: list[str] = []
    router = GatewayMessageRouter()
    router.on("stream_delta", lambda message: seen.append(str(message.payload["delta"])))

    async def run() -> None:
        await router.dispatch({"type": "stream_delta", "payload": {"delta": "hi"}})

    asyncio.run(run())
    assert seen == ["hi"]
