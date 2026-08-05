"""Gateway message dispatch for the TUI."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from keprix.tui.gateway_types import GatewayMessage, parse_gateway_message

GatewayCallback = Callable[[GatewayMessage], Awaitable[None] | None]


class GatewayMessageRouter:
    """Small async-aware router for typed gateway messages."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[GatewayCallback]] = {}

    def on(self, message_type: str, callback: GatewayCallback) -> None:
        self._handlers.setdefault(message_type, []).append(callback)

    async def dispatch(self, raw: GatewayMessage | dict[str, Any]) -> GatewayMessage:
        message = raw if isinstance(raw, GatewayMessage) else parse_gateway_message(raw)
        handlers = [*self._handlers.get(message.type, []), *self._handlers.get("*", [])]
        for handler in handlers:
            result = handler(message)
            if result is not None:
                await result
        return message

