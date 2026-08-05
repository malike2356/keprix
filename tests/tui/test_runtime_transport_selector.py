from __future__ import annotations

import pytest

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.http import HttpRuntimeTransport
from keprix.tui.runtime_transport.in_process import InProcessRuntimeTransport
from keprix.tui.runtime_transport.selector import select_runtime_transport
from keprix.tui.runtime_transport.websocket import WebSocketRuntimeTransport


@pytest.mark.asyncio
async def test_selector_respects_explicit_override() -> None:
    client = KeprixClient()
    assert isinstance(await select_runtime_transport(client, override="http"), HttpRuntimeTransport)
    assert isinstance(await select_runtime_transport(client, override="websocket"), WebSocketRuntimeTransport)
    assert isinstance(await select_runtime_transport(client, override="in_process"), InProcessRuntimeTransport)


@pytest.mark.asyncio
async def test_selector_falls_back_to_http_by_default() -> None:
    client = KeprixClient()
    transport = await select_runtime_transport(client, allow_in_process=False, websocket_available=False)
    assert isinstance(transport, HttpRuntimeTransport)


@pytest.mark.asyncio
async def test_selector_uses_websocket_when_available() -> None:
    client = KeprixClient()
    transport = await select_runtime_transport(client, allow_in_process=False, websocket_available=True)
    assert isinstance(transport, WebSocketRuntimeTransport)
