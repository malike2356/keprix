from __future__ import annotations

from keprix.tui.command_center.runtime_timeline import RuntimeTimeline, RuntimeTimelineEvent, render_runtime_timeline
from keprix.tui.runtime_store import RuntimeStore


def test_runtime_timeline_compacts_500_tool_events() -> None:
    timeline = RuntimeTimeline(max_items=600)
    for index in range(500):
        timeline.add(RuntimeTimelineEvent("tool", f"tool-{index}", status="done"))
    compact = timeline.compact_events(limit=12)
    assert len(compact) == 12
    assert compact[3].status == "summary"
    rendered = render_runtime_timeline(timeline, limit=12)
    assert "earlier runtime events" in rendered


def test_runtime_store_handles_100_subagents_in_timeline() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1")
    for index in range(100):
        store.spawn_subagent(str(index), label=f"agent-{index}")
        store.finish_subagent(str(index), status="done")
    assert len(store.subagents) == 100
    assert store.timeline.summary_counts()["subagent"] == 200
    assert len(store.timeline.compact_events(limit=15)) == 15
