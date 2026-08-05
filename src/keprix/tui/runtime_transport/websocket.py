"""WebSocket runtime transport adapter."""

from __future__ import annotations

from typing import AsyncIterator

from keprix.tui.client import KeprixClient
from keprix.tui.gateway_client import GatewayWebSocket
from keprix.tui.runtime_transport.events import RuntimeTransportEvent, normalize_gateway_event
from keprix.tui.runtime_transport.http import HttpRuntimeTransport


class WebSocketRuntimeTransport(HttpRuntimeTransport):
    mode = "websocket"

    def __init__(self, client: KeprixClient, gateway: GatewayWebSocket | None = None) -> None:
        super().__init__(client)
        self.gateway = gateway

    async def available(self) -> bool:
        if self.gateway is None:
            return False
        return self.gateway.connected

    async def normalize_gateway_payload(self, payload: dict, *, session_id: str = "") -> RuntimeTransportEvent:
        return normalize_gateway_event(payload, session_id=session_id)

    async def send_message_stream(self, session_id: str, content: str) -> AsyncIterator[RuntimeTransportEvent]:
        async for event in super().send_message_stream(session_id, content):
            yield RuntimeTransportEvent(type=event.type, payload=event.payload, session_id=event.session_id, source=self.mode)


__all__ = ["WebSocketRuntimeTransport"]
