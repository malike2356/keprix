from __future__ import annotations

from typing import Any, AsyncIterator

import pytest

from keprix.tui.client import ModelItem, RegistryItem, SessionItem, TuiConfig
from keprix.tui.runtime_transport.base import RuntimeTransport
from keprix.tui.runtime_transport.events import RuntimeTransportEvent


class ContractTransport:
    mode = "fake"

    async def health(self) -> bool:
        return True

    async def ensure_ready_session(self, session_id: str | None) -> str:
        return session_id or "s1"

    async def list_sessions(self) -> list[SessionItem]:
        return [SessionItem(id="s1", title="Session")]

    async def create_session(self, title: str = "New conversation") -> SessionItem:
        return SessionItem(id="s2", title=title)

    async def get_messages(self, session_id: str) -> tuple[str, list[dict[str, Any]]]:
        return "Session", [{"role": "assistant", "content": session_id}]

    async def list_models(self) -> list[ModelItem]:
        return [ModelItem(id="mini", provider="local", name="Mini")]

    async def send_message_stream(self, session_id: str, content: str) -> AsyncIterator[RuntimeTransportEvent]:
        yield RuntimeTransportEvent(type="text_delta", payload={"content": content}, session_id=session_id)
        yield RuntimeTransportEvent(type="message_done", payload={"usage": {"total_tokens": 1}}, session_id=session_id)

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        self.interrupted = (session_id, keep_queue)

    async def steer(self, session_id: str, text: str) -> int:
        return len(text)

    async def command_complete(self, prefix: str, *, session_id: str = "") -> list[str]:
        return ["/help"]

    async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict[str, Any]:
        return {"type": "exec", "output": f"{name}:{arg}:{session_id}"}

    async def list_skills(self) -> list[RegistryItem]:
        return [RegistryItem(name="skill")]

    async def list_plugins(self) -> list[RegistryItem]:
        return [RegistryItem(name="plugin")]

    async def get_tui_config(self) -> TuiConfig:
        return TuiConfig(
            busy_input_mode="interrupt",
            busy_input_modes=["interrupt", "queue", "steer"],
            details_modes={},
            compose_key="ctrl+g",
            voice_record_key="ctrl+b",
            voice_enabled=True,
        )


@pytest.mark.asyncio
async def test_runtime_transport_contract_surface() -> None:
    transport = ContractTransport()
    assert isinstance(transport, RuntimeTransport)
    assert await transport.health() is True
    assert await transport.ensure_ready_session(None) == "s1"
    assert (await transport.list_sessions())[0].id == "s1"
    assert (await transport.create_session()).id == "s2"
    assert (await transport.get_messages("s1"))[0] == "Session"
    assert (await transport.list_models())[0].id == "mini"
    assert await transport.steer("s1", "abc") == 3
    assert await transport.command_complete("/") == ["/help"]
    assert (await transport.command_dispatch("x", "y", session_id="s1"))["output"] == "x:y:s1"
    assert (await transport.list_skills())[0].name == "skill"
    assert (await transport.list_plugins())[0].name == "plugin"
    assert (await transport.get_tui_config()).busy_input_mode == "interrupt"
    events = [event async for event in transport.send_message_stream("s1", "hello")]
    assert [event.type for event in events] == ["text_delta", "message_done"]
    await transport.interrupt("s1", keep_queue=True)
    assert transport.interrupted == ("s1", True)
