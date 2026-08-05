from __future__ import annotations

import pytest

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.websocket import WebSocketRuntimeTransport


class FakeGateway:
    connected = True


@pytest.mark.asyncio
async def test_websocket_transport_reports_availability() -> None:
    transport = WebSocketRuntimeTransport(KeprixClient(), gateway=FakeGateway())  # type: ignore[arg-type]
    assert await transport.available() is True


@pytest.mark.asyncio
async def test_websocket_transport_normalizes_gateway_events() -> None:
    transport = WebSocketRuntimeTransport(KeprixClient())
    event = await transport.normalize_gateway_payload({"type": "stream_delta", "payload": {"content": "hi"}}, session_id="s1")
    assert event.type == "text_delta"
    assert event.source == "websocket"
    assert event.session_id == "s1"
