from __future__ import annotations

import pytest

from keprix.tui.app import KeprixTuiApp
from keprix.tui.client import KeprixClient, ModelItem, RegistryItem, SessionItem
from keprix.tui.details_runtime import render_runtime_details
from keprix.tui.runtime_events import ApiRuntimeEvent
from keprix.tui.runtime_store import RuntimeStore


class _Panel:
    def __init__(self) -> None:
        self.value = ""
        self.classes: list[str] = []

    def update(self, value: str) -> None:
        self.value = value

    def remove_class(self, name: str) -> None:
        if name in self.classes:
            self.classes.remove(name)
        return None

    def add_class(self, name: str) -> None:
        if name not in self.classes:
            self.classes.append(name)
        return None


def test_runtime_store_tracks_tools_subagents_messages_api_and_queue() -> None:
    store = RuntimeStore()
    store.start_turn(session_id="s1", model="mini")
    store.set_queue(["next"])
    store.start_tool("read_file", call_id="t1", args={"path": "README.md", "api_key": "secret"})
    store.finish_tool("read_file", call_id="t1", status="done", result_preview="ok")
    store.spawn_subagent("a1", label="Research")
    store.finish_subagent("a1", status="done", preview="complete")
    store.update_usage({"usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "cost": 0.01}})
    store.add_api_event(ApiRuntimeEvent(provider="openai", model="mini", status="done", latency_ms=25))
    store.finish_turn(status="complete")

    rendered = render_runtime_details(store)

    assert "Turn: complete" in rendered
    assert "Tokens: 15" in rendered
    assert "done      read_file" in rendered
    assert "api_key='[redacted]'" in rendered
    assert "done      Research" in rendered
    assert "done openai:mini 25 ms" in rendered
    assert store.queue == ["next"]


def test_app_runtime_panels_default_to_hidden(monkeypatch) -> None:
    app = KeprixTuiApp(client=KeprixClient(), session_id="s1")
    app._runtime_store.start_turn(session_id="s1", model="mini")
    app._runtime_store.add_api_event(ApiRuntimeEvent(provider="local", model="mini", status="done", latency_ms=25))
    panel = _Panel()
    timeline_calls: list[bool] = []
    sidebar_updates: list[bool] = []

    monkeypatch.setattr(app, "_thinking_panel", lambda: panel)
    monkeypatch.setattr(app, "_refresh_runtime_timeline", lambda: timeline_calls.append(True))
    monkeypatch.setattr(app, "_update_sidebar", lambda: sidebar_updates.append(True))

    app._refresh_thinking_panel()

    assert panel.value == ""
    assert "visible" not in panel.classes
    assert timeline_calls == [True]
    assert sidebar_updates == [True]


@pytest.mark.asyncio
async def test_timeline_slash_controls_visibility(monkeypatch) -> None:
    app = KeprixTuiApp(client=KeprixClient(), session_id="s1")
    app._runtime_store.start_turn(session_id="s1", model="mini")
    app._runtime_store.finish_turn(status="complete")
    calls: list[bool] = []
    monkeypatch.setattr(app, "_refresh_runtime_timeline", lambda: calls.append(app._timeline_panel_visible))

    shown = await app._slash_timeline([])
    hidden = await app._slash_timeline(["hide"])

    assert shown.message.startswith("Runtime timeline shown")
    assert hidden.message == "Runtime timeline hidden."
    assert calls == [True, False]


@pytest.mark.asyncio
async def test_app_run_turn_feeds_runtime_store() -> None:
    class Client(KeprixClient):
        async def stream_message(self, session_id: str, content: str):
            yield {"event": "tool_call", "name": "read_file", "tool_call_id": "t1", "args": {"path": "README.md"}}
            yield {"event": "tool_call_update", "name": "read_file", "tool_call_id": "t1", "status": "done", "result_preview": "ok"}
            yield {"event": "subagent_spawn", "subagent_id": "a1", "label": "Research"}
            yield {"event": "subagent_done", "subagent_id": "a1", "label": "Research", "status": "done", "summary": "complete"}
            yield {
                "event": "message_done",
                "model": "mini",
                "provider": "local",
                "usage": {"input_tokens": 4, "output_tokens": 6, "total_tokens": 10},
                "message": {"role": "assistant", "content": "done"},
            }

    app = KeprixTuiApp(client=Client(), session_id="s1")
    app.client.model = "mini"
    app._thinking_panel = lambda: _Panel()  # type: ignore[method-assign]
    app._set_busy = lambda busy: None  # type: ignore[method-assign]
    app._refresh_thinking_panel = lambda: None  # type: ignore[method-assign]
    app._update_status = lambda: None  # type: ignore[method-assign]
    app._log_agent_message = lambda body: None  # type: ignore[method-assign]
    app._log_system = lambda line: None  # type: ignore[method-assign]

    async def end_agent_stream() -> None:
        return None

    app._end_agent_stream = end_agent_stream  # type: ignore[method-assign]

    async def refresh_sessions() -> None:
        return None

    app.refresh_sessions = refresh_sessions  # type: ignore[method-assign]

    await app._run_turn("hello")

    assert app._runtime_store.turn.status == "complete"
    assert app._runtime_store.turn.total_tokens == 10
    assert app._runtime_store.tools[0].status == "done"
    assert app._runtime_store.subagents["a1"].status == "done"
    assert app._runtime_store.messages[-1].tool_calls == 1
    assert app._runtime_store.api_events[-1].provider == "local"


def test_runtime_registry_items_map_from_client_models() -> None:
    session = SessionItem(id="s1", title="Title", preview="Latest", last_active="2026-07-13")
    model = ModelItem(id="m1", provider="local", name="Mini", context_window=8192, pricing_input=0.1)
    registry = RegistryItem(name="researcher", description="Research skill", version="1.0")

    assert session.preview == "Latest"
    assert session.last_active == "2026-07-13"
    assert model.context_window == 8192
    assert model.pricing_input == 0.1
    assert registry.description == "Research skill"
