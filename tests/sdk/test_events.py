"""Unit tests for SDK event bus."""

from __future__ import annotations

import asyncio

import pytest

from keprix.sdk.events import SdkEventBus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    bus = SdkEventBus()
    queue = bus.subscribe("app-1")
    await bus.publish("app-1", {"steps": [{"entity": "Invoice"}]})
    payload = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert payload["steps"][0]["entity"] == "Invoice"
