from __future__ import annotations

import pytest

from keprix.tui.gateway_client import GatewayConfig, GatewayWebSocket


def test_gateway_config_defaults() -> None:
    config = GatewayConfig(ws_url="http://127.0.0.1:3333")
    assert config.reconnect_initial_delay == 1.0
    assert config.reconnect_max_delay == 30.0
    assert config.ping_interval == 30.0


@pytest.mark.asyncio
async def test_gateway_send_when_disconnected_does_not_raise() -> None:
    gateway = GatewayWebSocket("http://127.0.0.1:3333")
    await gateway.send({"type": "ping"})
    assert gateway.connected is False


def test_gateway_dispatch_routes_callbacks() -> None:
    gateway = GatewayWebSocket("http://127.0.0.1:3333")
    deltas: list[str] = []
    tools: list[str] = []
    statuses: list[int] = []
    errors: list[str] = []
    gateway.on_delta = lambda event: deltas.append(event.text)
    gateway.on_tool_progress = lambda event: tools.append(event.tool_name)
    gateway.on_turn_status = lambda event: statuses.append(event.queue_depth)
    gateway.on_error = errors.append

    gateway._dispatch({"type": "delta", "text": "hi"})
    gateway._dispatch({"type": "tool_progress", "tool_name": "read_file"})
    gateway._dispatch({"type": "turn_status", "queue_depth": 2})
    gateway._dispatch({"type": "error", "message": "failed"})

    assert deltas == ["hi"]
    assert tools == ["read_file"]
    assert statuses == [2]
    assert errors == ["failed"]
