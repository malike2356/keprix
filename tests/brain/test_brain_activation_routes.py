import asyncio

import pytest

from keprix.api.brain_activation_routes import _events
from keprix.brain.activation_bus import activation_bus


class _OpenRequest:
    async def is_disconnected(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_activation_stream_filters_by_session() -> None:
    generator = _events(_OpenRequest(), "workspace-route", "session-live")
    next_chunk = asyncio.create_task(anext(generator))
    try:
        await asyncio.sleep(0)
        await activation_bus.publish(
            "workspace-route",
            {"type": "tool_called", "session_id": "other-session", "node_kind": "tool", "node_id": "ignored"},
        )
        await activation_bus.publish(
            "workspace-route",
            {"type": "tool_called", "session_id": "session-live", "node_kind": "tool", "node_id": "search"},
        )

        chunk = await asyncio.wait_for(next_chunk, timeout=1)
        assert chunk.startswith(b"data: ")
        assert b'"session_id": "session-live"' in chunk
        assert b'"node_id": "search"' in chunk
        assert b"ignored" not in chunk
    finally:
        await generator.aclose()
