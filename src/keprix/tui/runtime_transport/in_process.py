"""Safe in-process runtime transport boundary."""

from __future__ import annotations

from typing import Any, AsyncIterator

from keprix.tui.client import KeprixClient
from keprix.tui.runtime_transport.events import RuntimeTransportEvent, normalize_runtime_event
from keprix.tui.runtime_transport.http import HttpRuntimeTransport


class InProcessRuntimeTransport(HttpRuntimeTransport):
    mode = "in_process"

    def __init__(self, client: KeprixClient, runtime: Any | None = None) -> None:
        super().__init__(client)
        self.runtime = runtime

    async def available(self) -> bool:
        return self.runtime is not None

    async def health(self) -> bool:
        if self.runtime is None:
            return False
        health = getattr(self.runtime, "health", None)
        if health is None:
            return True
        result = health()
        if hasattr(result, "__await__"):
            result = await result
        return bool(result)

    async def send_message_stream(self, session_id: str, content: str) -> AsyncIterator[RuntimeTransportEvent]:
        if self.runtime is None or not hasattr(self.runtime, "send_message_stream"):
            async for event in super().send_message_stream(session_id, content):
                yield event
            return
        stream = self.runtime.send_message_stream(session_id, content)
        async for payload in stream:
            if isinstance(payload, RuntimeTransportEvent):
                yield payload
            else:
                yield normalize_runtime_event(dict(payload), source=self.mode, session_id=session_id)

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        if self.runtime is not None and hasattr(self.runtime, "interrupt"):
            result = self.runtime.interrupt(session_id, keep_queue=keep_queue)
            if hasattr(result, "__await__"):
                await result
            return
        await super().interrupt(session_id, keep_queue=keep_queue)


def load_in_process_runtime() -> Any | None:
    """Try to load an in-process runtime without import-time side effects."""
    try:
        from keprix.runtime import get_tui_runtime  # type: ignore
    except Exception:
        return None
    try:
        return get_tui_runtime()
    except Exception:
        return None


__all__ = ["InProcessRuntimeTransport", "load_in_process_runtime"]
