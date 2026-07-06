"""Background self-configuration service for the gateway."""

from __future__ import annotations

from typing import Any

from keprix.config.auto_repair import handle_health_change
from keprix.config.health_monitor import get_health_monitor
from keprix.gateway.adapter_registry import register_adapter, unregister_adapter


class _LiveChannelAdapter:
    def __init__(self, name: str, adapter: Any) -> None:
        self.name = name
        self._adapter = adapter

    async def health_check(self) -> None:
        connected = getattr(self._adapter, "is_connected", None)
        if callable(connected) and not connected():
            raise RuntimeError("adapter is disconnected")

    async def reconnect(self) -> None:
        reconnect = getattr(self._adapter, "reconnect", None)
        if callable(reconnect):
            await reconnect()
            return
        raise RuntimeError("adapter does not support reconnect")


def register_gateway_adapters(adapters: dict[Any, Any]) -> None:
    for platform, adapter in adapters.items():
        name = str(getattr(platform, "value", platform)).lower()
        register_adapter(_LiveChannelAdapter(name, adapter))


def clear_gateway_adapters(adapters: dict[Any, Any]) -> None:
    for platform in adapters:
        name = str(getattr(platform, "value", platform)).lower()
        unregister_adapter(name)


def start_self_config_service(adapters: dict[Any, Any] | None = None) -> None:
    """Start health monitoring with auto-repair when the gateway is running."""
    if adapters:
        register_gateway_adapters(adapters)

    monitor = get_health_monitor()
    if not monitor._callbacks:
        monitor.on_status_change(handle_health_change)
    monitor.start_background()
