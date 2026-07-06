"""Tests for AG-UI adapter."""

from __future__ import annotations

import json

import pytest

from keprix.interfaces.ag_ui_adapter import ag_ui_event, handle_ag_ui, serialize_ag_ui_stream
from keprix.interfaces.interface_registry import InterfaceKind, InterfaceRegistry
from keprix.interfaces.interface_registry import _api_handler, _web_ui_handler


@pytest.fixture
def registry() -> InterfaceRegistry:
    reg = InterfaceRegistry()
    from keprix.interfaces.ag_ui_adapter import handle_ag_ui as ag_handler

    reg.register_handler(InterfaceKind.WEB_UI, _web_ui_handler)
    reg.register_handler(InterfaceKind.API, _api_handler)
    reg.register_handler(InterfaceKind.AG_UI, ag_handler)
    reg.bind_agent("demo-agent", [InterfaceKind.WEB_UI, InterfaceKind.AG_UI])
    return reg


def test_ag_ui_event_includes_trace() -> None:
    event = ag_ui_event("run_started", trace_id="trace-1", agent_id="demo-agent", payload={"input": "hi"})
    assert event["trace_id"] == "trace-1"
    assert event["type"] == "run_started"


@pytest.mark.asyncio
async def test_ag_ui_adapter_returns_event_stream(monkeypatch, registry: InterfaceRegistry) -> None:
    monkeypatch.setattr("keprix.interfaces.interface_registry.get_interface_registry", lambda: registry)
    result = await handle_ag_ui(agent_id="demo-agent", trace_id="trace-abc", message="hello")
    assert result["trace_id"] == "trace-abc"
    events = result["events"]
    assert events[0]["type"] == "run_started"
    assert events[-1]["type"] == "run_finished"
    stream = serialize_ag_ui_stream(events)
    assert len(stream.splitlines()) == len(events)
    parsed = json.loads(stream.splitlines()[0])
    assert parsed["agent_id"] == "demo-agent"
