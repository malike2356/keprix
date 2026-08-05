from __future__ import annotations

import time

import pytest

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.in_process import InProcessRuntimeTransport


class FastRuntime:
    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        self.session_id = session_id


@pytest.mark.asyncio
async def test_in_process_interrupt_latency_is_immediate() -> None:
    runtime = FastRuntime()
    transport = InProcessRuntimeTransport(KeprixClient(), runtime)
    started = time.perf_counter()
    await transport.interrupt("s1")
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert elapsed_ms < 20
    assert runtime.session_id == "s1"
