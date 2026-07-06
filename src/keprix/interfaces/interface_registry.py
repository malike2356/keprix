"""Agent interface registry across channels and protocols."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Awaitable, Callable


class InterfaceKind(str, Enum):
    WEB_UI = "web_ui"
    SLACK = "slack"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    API = "api"
    A2A = "a2a"
    AG_UI = "ag_ui"


@dataclass
class InterfaceBinding:
    agent_id: str
    kind: InterfaceKind
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InterfaceDispatchResult:
    ok: bool
    channel: str
    trace_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


Handler = Callable[..., Awaitable[dict[str, Any]]]


class InterfaceRegistry:
    def __init__(self) -> None:
        self._bindings: dict[str, list[InterfaceBinding]] = {}
        self._handlers: dict[InterfaceKind, Handler] = {}

    def register_handler(self, kind: InterfaceKind, handler: Handler) -> None:
        self._handlers[kind] = handler

    def bind_agent(self, agent_id: str, kinds: list[InterfaceKind], *, metadata: dict[str, Any] | None = None) -> list[InterfaceBinding]:
        bindings = [
            InterfaceBinding(agent_id=agent_id, kind=kind, metadata=dict(metadata or {}))
            for kind in kinds
        ]
        self._bindings[agent_id] = bindings
        return bindings

    def list_bindings(self, agent_id: str | None = None) -> list[InterfaceBinding]:
        if agent_id:
            return list(self._bindings.get(agent_id, []))
        items: list[InterfaceBinding] = []
        for bindings in self._bindings.values():
            items.extend(bindings)
        return items

    def supported_kinds(self, agent_id: str) -> list[str]:
        return [binding.kind.value for binding in self._bindings.get(agent_id, []) if binding.enabled]

    async def dispatch(
        self,
        agent_id: str,
        kind: InterfaceKind,
        *,
        trace_id: str | None = None,
        **payload: Any,
    ) -> InterfaceDispatchResult:
        trace = trace_id or str(uuid.uuid4())
        bindings = self._bindings.get(agent_id, [])
        if bindings and not any(binding.kind == kind and binding.enabled for binding in bindings):
            return InterfaceDispatchResult(ok=False, channel=kind.value, trace_id=trace, error="interface not enabled for agent")
        handler = self._handlers.get(kind)
        if handler is None:
            return InterfaceDispatchResult(ok=False, channel=kind.value, trace_id=trace, error="handler not registered")
        try:
            result = await handler(agent_id=agent_id, trace_id=trace, **payload)
            return InterfaceDispatchResult(ok=True, channel=kind.value, trace_id=trace, payload=result)
        except Exception as exc:
            return InterfaceDispatchResult(ok=False, channel=kind.value, trace_id=trace, error=str(exc))

    async def dispatch_stream(
        self,
        agent_id: str,
        kind: InterfaceKind,
        *,
        trace_id: str | None = None,
        **payload: Any,
    ) -> AsyncIterator[Any]:
        from keprix.interfaces.web_ui_stream_events import GatewayStreamEvent

        trace = trace_id or str(uuid.uuid4())
        bindings = self._bindings.get(agent_id, [])
        if bindings and not any(binding.kind == kind and binding.enabled for binding in bindings):
            yield GatewayStreamEvent("error", {"message": "interface not enabled for agent"})
            yield GatewayStreamEvent("done", {})
            return
        handler = self._handlers.get(kind)
        if handler is None:
            yield GatewayStreamEvent("error", {"message": "handler not registered"})
            yield GatewayStreamEvent("done", {})
            return
        try:
            stream = await handler(agent_id=agent_id, trace_id=trace, stream=True, **payload)
            async for event in stream:
                yield event
        except Exception as exc:
            yield GatewayStreamEvent("error", {"message": str(exc)})
            yield GatewayStreamEvent("done", {})


_registry: InterfaceRegistry | None = None


def get_interface_registry() -> InterfaceRegistry:
    global _registry
    if _registry is None:
        _registry = InterfaceRegistry()
        _register_default_handlers(_registry)
    return _registry


def _register_default_handlers(registry: InterfaceRegistry) -> None:
    from keprix.interfaces.ag_ui_adapter import handle_ag_ui
    from keprix.interfaces.a2a_interface import handle_a2a
    from keprix.interfaces.discord_interface import handle_discord
    from keprix.interfaces.slack_interface import handle_slack
    from keprix.interfaces.telegram_interface import handle_telegram
    from keprix.interfaces.whatsapp_interface import handle_whatsapp

    from keprix.interfaces.web_ui_stream import _web_ui_handler

    registry.register_handler(InterfaceKind.WEB_UI, _web_ui_handler)
    registry.register_handler(InterfaceKind.API, _api_handler)
    registry.register_handler(InterfaceKind.SLACK, handle_slack)
    registry.register_handler(InterfaceKind.TELEGRAM, handle_telegram)
    registry.register_handler(InterfaceKind.WHATSAPP, handle_whatsapp)
    registry.register_handler(InterfaceKind.DISCORD, handle_discord)
    registry.register_handler(InterfaceKind.A2A, handle_a2a)
    registry.register_handler(InterfaceKind.AG_UI, handle_ag_ui)


async def _api_handler(*, agent_id: str, trace_id: str, message: str = "", **kwargs: Any) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "trace_id": trace_id,
        "message": message or kwargs.get("text", ""),
        "status": "accepted",
    }
