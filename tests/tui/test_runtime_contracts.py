from __future__ import annotations

from keprix.tui.runtime.adapters import api_event_from_payload
from keprix.tui.runtime.api_inspector import latest_api_event
from keprix.tui.runtime.details import render_runtime_details
from keprix.tui.runtime.events import MessageRuntimeMetadata, ToolRuntimeEvent
from keprix.tui.runtime.store import RuntimeStore
from keprix.tui.runtime.subagents import active_subagents
from keprix.tui.runtime.tools import running_tools


def test_runtime_package_preserves_store_behavior() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1", model="mini", provider="local")
    store.start_tool("scan", args={"api_key": "secret"})
    store.finish_tool("done", call_id="missing", result_preview="ok")
    store.spawn_subagent("a1", label="review")
    store.add_message_metadata(MessageRuntimeMetadata(message_id="m1", total_tokens=42))
    rendered = render_runtime_details(store)
    assert "Turn: running" in rendered
    assert "Tools:" in rendered
    assert "Subagents:" in rendered


def test_runtime_helpers_filter_live_data() -> None:
    assert running_tools([ToolRuntimeEvent(name="a"), ToolRuntimeEvent(name="b", status="done")])[0].name == "a"
    store = RuntimeStore()
    store.spawn_subagent("a1", label="planner")
    store.finish_subagent("a2", label="done")
    assert [item.label for item in active_subagents(store.subagents)] == ["planner"]


def test_api_inspector_adapter_is_stable() -> None:
    event = api_event_from_payload({"provider": "openai", "model": "mini", "status": "ok", "latency_ms": 25})
    assert latest_api_event([event]) is event
    assert event.provider == "openai"
