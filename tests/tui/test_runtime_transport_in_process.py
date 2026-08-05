from __future__ import annotations

from typing import AsyncIterator

import pytest

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.events import RuntimeTransportEvent
from keprix.tui.runtime_transport.in_process import InProcessRuntimeTransport, load_in_process_runtime


class FakeRuntime:
    async def health(self) -> bool:
        return True

    async def send_message_stream(self, session_id: str, content: str) -> AsyncIterator[dict]:
        yield {"type": "delta", "content": content, "session_id": session_id}

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        self.interrupted = (session_id, keep_queue)


@pytest.mark.asyncio
async def test_in_process_transport_uses_runtime_when_available() -> None:
    runtime = FakeRuntime()
    transport = InProcessRuntimeTransport(KeprixClient(), runtime)
    assert await transport.available() is True
    assert await transport.health() is True
    events = [event async for event in transport.send_message_stream("s1", "hello")]
    assert events == [RuntimeTransportEvent(type="text_delta", payload={"content": "hello"}, session_id="s1", source="in_process")]
    await transport.interrupt("s1", keep_queue=True)
    assert runtime.interrupted == ("s1", True)


def test_in_process_loader_falls_back_safely() -> None:
    assert load_in_process_runtime() is None
