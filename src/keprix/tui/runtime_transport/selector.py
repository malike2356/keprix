"""Runtime transport selection."""

from __future__ import annotations

import os

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.base import RuntimeTransport
from keprix.tui.runtime_transport.http import HttpRuntimeTransport
from keprix.tui.runtime_transport.in_process import InProcessRuntimeTransport, load_in_process_runtime
from keprix.tui.runtime_transport.websocket import WebSocketRuntimeTransport


async def select_runtime_transport(
    client: KeprixClient,
    *,
    override: str | None = None,
    allow_in_process: bool = True,
    websocket_available: bool = False,
) -> RuntimeTransport:
    mode = (override or os.environ.get("KEPRIX_TUI_TRANSPORT") or "").strip().lower()
    if mode == "http":
        return HttpRuntimeTransport(client)
    if mode == "websocket":
        return WebSocketRuntimeTransport(client)
    if mode == "in_process":
        return InProcessRuntimeTransport(client, load_in_process_runtime())

    if allow_in_process:
        runtime = load_in_process_runtime()
        if runtime is not None:
            transport = InProcessRuntimeTransport(client, runtime)
            if await transport.health():
                return transport
    if websocket_available:
        return WebSocketRuntimeTransport(client)
    return HttpRuntimeTransport(client)


__all__ = ["select_runtime_transport"]
