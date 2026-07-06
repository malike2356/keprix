"""Routing tests for workspace chat streaming."""

from __future__ import annotations

from typing import Any

import pytest

from keprix.api.conversation_routes import _stream_assistant_reply


@pytest.mark.asyncio
async def test_stream_assistant_reply_uses_llm_for_normal_chat(monkeypatch):
    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "false")
    seen: dict[str, Any] = {}

    async def fake_agent_reply(**kwargs: Any) -> str:
        seen["agent_called"] = True
        return "slash output"

    async def fake_stream_chat_completion(**kwargs: Any):
        seen["stream_kwargs"] = kwargs
        yield "Keprix "
        yield "summary"

    monkeypatch.setattr(
        "keprix.api.conversation_routes._agent_reply_text",
        fake_agent_reply,
    )
    monkeypatch.setattr(
        "keprix.api.conversation_routes.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="Summarise what Keprix can do in this workspace",
            model="deepseek:deepseek-chat",
            user_id="web",
            history=[],
        )
    ]

    assert seen.get("agent_called") is not True
    assert seen["stream_kwargs"]["user_text"] == "Summarise what Keprix can do in this workspace"
    assert (
        "".join(event.get("content", "") for event in events if event.get("event") == "text_delta")
        == "Keprix summary"
    )


@pytest.mark.asyncio
async def test_stream_assistant_reply_uses_slash_handler_for_commands(monkeypatch):
    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "false")
    seen: dict[str, Any] = {}

    async def fake_agent_reply(**kwargs: Any) -> str:
        seen["agent_called"] = True
        return "status ok"

    async def fake_stream_chat_completion(**kwargs: Any):
        seen["stream_called"] = True
        yield "should not run"
        return
        yield  # pragma: no cover

    monkeypatch.setattr(
        "keprix.api.conversation_routes._agent_reply_text",
        fake_agent_reply,
    )
    monkeypatch.setattr(
        "keprix.api.conversation_routes.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="/status",
            model="deepseek:deepseek-chat",
            user_id="web",
            history=[],
        )
    ]

    assert seen.get("agent_called") is True
    assert seen.get("stream_called") is not True
    assert any(event.get("event") == "text_done" for event in events)


@pytest.mark.asyncio
async def test_stream_assistant_reply_uses_llm_when_message_mentions_mutation(monkeypatch):
    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "false")
    seen: dict[str, Any] = {}

    async def fake_agent_reply(**kwargs: Any) -> str:
        seen["agent_called"] = True
        return "slash output"

    async def fake_stream_chat_completion(**kwargs: Any):
        seen["stream_called"] = True
        yield "mutation "
        yield "explained"

    monkeypatch.setattr(
        "keprix.api.conversation_routes._agent_reply_text",
        fake_agent_reply,
    )
    monkeypatch.setattr(
        "keprix.api.conversation_routes.stream_chat_completion",
        fake_stream_chat_completion,
    )

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="is that your mutation capability?",
            model="deepseek:deepseek-chat",
            user_id="web",
            history=[],
        )
    ]

    assert seen.get("agent_called") is not True
    assert seen.get("stream_called") is True
    assert any(event.get("event") == "text_done" for event in events)


@pytest.mark.asyncio
async def test_stream_assistant_reply_gateway_flag_routes_slash(monkeypatch):
    from keprix.interfaces.interface_registry import InterfaceRegistry
    from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent

    seen: dict[str, Any] = {}

    async def fake_dispatch_stream(self, agent_id, kind, **payload):
        seen["slash_message"] = payload.get("message")
        yield GatewayStreamEvent("text_delta", {"content": "tools "})
        yield GatewayStreamEvent("text_delta", {"content": "listed"})
        yield GatewayStreamEvent("text_done", {})
        yield GatewayStreamEvent("done", {})

    monkeypatch.setenv("KEPRIX_CHAT_GATEWAY_STREAM", "true")
    monkeypatch.setattr(InterfaceRegistry, "dispatch_stream", fake_dispatch_stream)

    events = [
        event
        async for event in _stream_assistant_reply(
            user_text="/tools",
            model=None,
            user_id="web",
        )
    ]

    assert seen.get("slash_message") == "/tools"
    assert any(event.get("event") == "text_done" for event in events)
    assert "".join(event.get("content", "") for event in events if event.get("event") == "text_delta") == "tools listed"
