from __future__ import annotations

from keprix.tui.command_center.runtime_timeline import RuntimeTimeline, RuntimeTimelineEvent, render_runtime_timeline
from keprix.tui.runtime_events import ApiRuntimeEvent, MessageRuntimeMetadata
from keprix.tui.runtime_store import RuntimeStore
from keprix.tui.widgets.runtime_timeline import RuntimeTimelineWidget


def test_runtime_store_records_timeline_events() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1", model="mini", provider="local")
    store.start_tool("scan", call_id="t1")
    store.finish_tool("scan", call_id="t1", status="done", result_preview="ok")
    store.spawn_subagent("a1", label="Research", preview="checking")
    store.finish_subagent("a1", status="done", preview="complete")
    store.update_usage({"usage": {"input_tokens": 4, "output_tokens": 6, "total_tokens": 10, "cost": 0.01}})
    store.add_message_metadata(MessageRuntimeMetadata(model="mini", total_tokens=10))
    store.add_api_event(ApiRuntimeEvent(provider="local", model="mini", status="done", latency_ms=25))
    store.set_queue(["next"])
    store.finish_turn(status="complete")
    rendered = render_runtime_timeline(store.timeline)
    assert "Turn started" in rendered
    assert "scan" in rendered
    assert "Research" in rendered
    assert "10 tokens" in rendered
    assert "local:mini" in rendered
    assert "1 queued" in rendered


def test_runtime_timeline_exposes_summary_counts() -> None:
    timeline = RuntimeTimeline()
    timeline.add(RuntimeTimelineEvent("turn", "Turn started"))
    timeline.add(RuntimeTimelineEvent("tool", "scan", status="running"))
    timeline.add(RuntimeTimelineEvent("tool", "scan", status="done"))
    assert timeline.summary_counts() == {"turn": 1, "tool": 2}


def test_runtime_timeline_widget_updates_and_hides() -> None:
    widget = RuntimeTimelineWidget("")
    timeline = RuntimeTimeline()
    timeline.add(RuntimeTimelineEvent("turn", "Turn started"))
    widget.update_timeline(timeline, visible=True)
    assert widget.display is True
    widget.update_timeline(timeline, visible=False)
    assert widget.display is False
