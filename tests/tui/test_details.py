"""Tests for TUI details sections (Prompt 206)."""

from __future__ import annotations

from keprix.tui.details import (
    ActivityFeed,
    DetailsConfig,
    SubagentList,
    ToolTrail,
    cycle_mode,
    render_details_panel,
)


def test_cycle_mode_order() -> None:
    assert cycle_mode("hidden") == "collapsed"
    assert cycle_mode("collapsed") == "expanded"
    assert cycle_mode("expanded") == "hidden"
    assert cycle_mode("unknown") == "collapsed"


def test_tool_trail_collapsed_and_expanded() -> None:
    trail = ToolTrail()
    trail.start_tool("web_search")
    trail.finish_tool("web_search")
    trail.start_tool("terminal")
    config = DetailsConfig()
    config.set_mode("tools", "collapsed")
    collapsed = trail.render_tools(config.modes["tools"])
    assert collapsed == ["[tools] 1 running, 1 done"]
    config.set_mode("tools", "expanded")
    expanded = trail.render_tools(config.modes["tools"])
    assert expanded[0] == "[tools] 1 running, 1 done"
    assert any("web_search" in line for line in expanded)
    assert any("terminal" in line for line in expanded)


def test_subagent_list_render() -> None:
    subagents = SubagentList()
    subagents.spawn("sa-1", label="coder-1 refactor auth/")
    subagents.complete("sa-1", label="coder-1 refactor auth/", cost_hint="$0.02")
    config = DetailsConfig()
    config.set_mode("subagents", "expanded")
    lines = subagents.render(config.modes["subagents"])
    assert lines[0] == "[subagents]"
    assert any("coder-1" in line for line in lines)


def test_activity_feed_max_eight_lines() -> None:
    feed = ActivityFeed(max_lines=8)
    for idx in range(12):
        feed.push(f"line-{idx}")
    config = DetailsConfig()
    config.set_mode("activity", "expanded")
    rendered = feed.render(config.modes["activity"])
    assert rendered[0] == "[activity]"
    assert len(rendered) == 9
    assert "line-4" in rendered[1]
    assert "line-11" in rendered[-1]


def test_render_details_panel_hides_sections() -> None:
    trail = ToolTrail()
    trail.start_tool("grep")
    subagents = SubagentList()
    subagents.spawn("sa-2", label="worker")
    activity = ActivityFeed()
    activity.push("Prefetching context...")
    config = DetailsConfig()
    config.set_all("hidden")
    assert render_details_panel(
        config=config,
        trail=trail,
        subagents=subagents,
        activity=activity,
    ) == ""
