from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from keprix.tui.client import RegistryItem, SessionItem, TuiConfig
from keprix.tui.runtime_transport.http import HttpRuntimeTransport


class FakeHttpClient:
    async def health_check(self) -> bool:
        return True

    async def ensure_ready_session(self, session_id: str | None) -> str:
        return session_id or "s1"

    async def list_sessions(self) -> list[SessionItem]:
        return [SessionItem(id="s1", title="A")]

    async def create_session(self, title: str = "New conversation") -> SessionItem:
        return SessionItem(id="s2", title=title)

    async def get_messages(self, session_id: str) -> tuple[str, list[dict[str, Any]]]:
        return "A", []

    async def list_models(self) -> list:
        return []

    async def stream_message(self, session_id: str, content: str) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "delta", "content": content}
        yield {"type": "done", "usage": {"total_tokens": 2}}

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        self.interrupt_args = (session_id, keep_queue)

    async def steer(self, session_id: str, text: str) -> int:
        return len(text)

    async def slash_complete(self, prefix: str, *, session_id: str = "") -> list[str]:
        return ["/help"]

    async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict[str, Any]:
        return {"output": name}

    async def list_skills(self) -> list[RegistryItem]:
        return []

    async def list_plugins(self) -> list[RegistryItem]:
        return []

    async def get_tui_config(self) -> TuiConfig:
        return TuiConfig("interrupt", ["interrupt"], {}, "ctrl+g", "ctrl+b", True)

    async def slash_exec(self, command: str, *, session_id: str = "") -> dict[str, Any]:
        return {"ok": True, "output": command}


@pytest.mark.asyncio
async def test_http_transport_delegates_and_normalizes_stream() -> None:
    client = FakeHttpClient()
    transport = HttpRuntimeTransport(client)  # type: ignore[arg-type]
    assert await transport.health() is True
    events = [event async for event in transport.send_message_stream("s1", "hello")]
    assert [event.type for event in events] == ["text_delta", "message_done"]
    assert events[0].payload["content"] == "hello"
    await transport.interrupt("s1", keep_queue=True)
    assert client.interrupt_args == ("s1", True)
    assert await transport.command_complete("/") == ["/help"]
    assert (await transport.slash_exec("help"))["output"] == "help"
