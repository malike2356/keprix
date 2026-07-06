"""Tests for WEB_UI gateway NDJSON stream bridge (Prompt 142)."""

from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from keprix.api.conversation_routes import _stream_assistant_reply
from keprix.interfaces.interface_registry import InterfaceKind, InterfaceRegistry
from keprix.interfaces.web_ui_stream import iter_web_ui_gateway_stream
from keprix.interfaces.web_ui_stream_events import (
    GatewayStreamEvent,
    map_gateway_event_to_ndjson,
)


@pytest.mark.asyncio
async def test_map_gateway_event_to_ndjson_shapes():
    assert map_gateway_event_to_ndjson(
        GatewayStreamEvent("text_delta", {"content": "hi"})
    ) == {"event": "text_delta", "content": "hi"}
    assert map_gateway_event_to_ndjson(
        GatewayStreamEvent(
            "mutation",
            {
                "id": "mut-1",
                "toolName": "fetch_stock_price",
                "approach": "gap",
                "code": "print(1)",
                "skillYaml": "name: fetch_stock_price",
                "sandboxResult": "ok",
                "sandboxExitCode": 0,
                "sandboxStderr": "",
                "status": "pending",
            },
        )
    )["event"] == "mutation"
    assert map_gateway_event_to_ndjson(
        GatewayStreamEvent("tool_call", {"name": "todo", "input": {"q": "x"}, "status": "running"})
    ) == {
        "event": "tool_call",
        "name": "todo",
        "input": {"q": "x"},
        "status": "running",
    }


@pytest.mark.asyncio
async def test_iter_web_ui_gateway_stream_emits_tool_sequence(monkeypatch):
    async def fake_mutation_turn(**_kwargs: Any) -> AsyncIterator[GatewayStreamEvent]:
        if False:
            yield GatewayStreamEvent("text_delta", {"content": "nope"})
        return
        yield  # pragma: no cover

    async def fake_agent_loop(**_kwargs: Any) -> AsyncIterator[GatewayStreamEvent]:
        yield GatewayStreamEvent("tool_call", {"name": "todo", "input": {}, "status": "running"})
        yield GatewayStreamEvent(
            "tool_call_update",
            {"name": "todo", "output": "done", "status": "done"},
        )
        yield GatewayStreamEvent("text_delta", {"content": "All set."})
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})

    monkeypatch.setattr("keprix.interfaces.web_ui_stream._stream_mutation_turn", fake_mutation_turn)
    monkeypatch.setattr("keprix.interfaces.web_ui_stream.web_ui_agent_loop_enabled", lambda: True)
    monkeypatch.setattr("keprix.interfaces.web_ui_stream._stream_agent_tool_loop", fake_agent_loop)

    events = [
        event
        async for event in iter_web_ui_gateway_stream(
            agent_id="default",
            trace_id="trace-1",
            message="list todos",
            user_id="web",
        )
    ]
    kinds = [event.event for event in events]
    assert "tool_call" in kinds
    assert "tool_call_update" in kinds
    assert any(event.event == "text_delta" for event in events)


@pytest.mark.asyncio
async def test_stream_assistant_reply_uses_gateway_dispatch_when_flag_on(monkeypatch):
    seen: dict[str, Any] = {}

    async def fake_dispatch_stream(self, agent_id, kind, **payload):
        seen["agent_id"] = agent_id
        seen["kind"] = kind
        seen["payload"] = payload
        yield GatewayStreamEvent("text_delta", {"content": "gateway "})
        yield GatewayStreamEvent("text_delta", {"content": "reply"})
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})

    async def fake_stream_chat_completion(**_kwargs: Any):
        seen["legacy_stream"] = True
        yield "should not run"
        return
        yield  # pragma: no cover

    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "true")
    monkeypatch.setattr(
        InterfaceRegistry,
        "dispatch_stream",
        fake_dispatch_stream,
    )
    monkeypatch.setattr(
        "keprix.api.conversation_routes.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="hello",
            model="deepseek:deepseek-chat",
            user_id="web",
            history=[],
        )
    ]

    assert seen["agent_id"] == "default"
    assert seen["kind"] == InterfaceKind.WEB_UI
    assert seen.get("legacy_stream") is not True
    assert "".join(event.get("content", "") for event in events if event.get("event") == "text_delta") == "gateway reply"
    assert any(event.get("event") == "text_done" for event in events)


@pytest.mark.asyncio
async def test_stream_assistant_reply_gateway_mutation_event(monkeypatch):
    async def fake_dispatch_stream(self, agent_id, kind, **payload):
        yield GatewayStreamEvent(
            "mutation",
            {
                "id": "mut-99",
                "toolName": "fetch_stock_price",
                "approach": "stock gap",
                "code": "print('ok')",
                "skillYaml": "name: fetch_stock_price",
                "sandboxResult": "ok",
                "sandboxExitCode": 0,
                "sandboxStderr": "",
                "status": "pending",
            },
        )
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})

    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "true")
    monkeypatch.setattr(InterfaceRegistry, "dispatch_stream", fake_dispatch_stream)

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="fetch AAPL stock price",
            model=None,
            user_id="web",
        )
    ]
    mutation = [event for event in events if event.get("event") == "mutation"]
    assert len(mutation) == 1
    assert mutation[0]["toolName"] == "fetch_stock_price"


@pytest.mark.asyncio
async def test_stream_assistant_reply_flag_off_uses_legacy_llm(monkeypatch):
    seen: dict[str, Any] = {}

    async def fake_dispatch_stream(self, *_args, **_kwargs):
        seen["gateway"] = True
        yield GatewayStreamEvent("text_delta", {"content": "nope"})
        return
        yield  # pragma: no cover

    async def fake_stream_chat_completion(**kwargs: Any):
        seen["stream_kwargs"] = kwargs
        yield "legacy "

    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "false")
    monkeypatch.setattr(InterfaceRegistry, "dispatch_stream", fake_dispatch_stream)
    monkeypatch.setattr(
        "keprix.api.conversation_routes.stream_chat_completion",
        fake_stream_chat_completion,
    )
    monkeypatch.setattr(
        "keprix.agent.keprix.chat_mutation_bridge.maybe_run_mutation_for_chat",
        lambda **_kwargs: _empty_async_gen(),
    )

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="plain chat",
            model="deepseek:deepseek-chat",
            user_id="web",
        )
    ]

    assert seen.get("gateway") is not True
    assert seen["stream_kwargs"]["user_text"] == "plain chat"
    assert any(event.get("event") == "text_delta" for event in events)


async def _empty_async_gen():
    if False:
        yield {}
