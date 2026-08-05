"""HTTP runtime transport adapter."""

from __future__ import annotations

from typing import Any, AsyncIterator

from keprix.tui.client import KeprixClient, ModelItem, RegistryItem, SessionItem, TuiConfig
from keprix.tui.runtime_transport.events import RuntimeTransportEvent, normalize_runtime_event


class HttpRuntimeTransport:
    mode = "http"

    def __init__(self, client: KeprixClient) -> None:
        self.client = client

    async def health(self) -> bool:
        return await self.client.health_check()

    async def ensure_ready_session(self, session_id: str | None) -> str:
        return await self.client.ensure_ready_session(session_id)

    async def list_sessions(self) -> list[SessionItem]:
        return await self.client.list_sessions()

    async def create_session(self, title: str = "New conversation") -> SessionItem:
        return await self.client.create_session(title)

    async def get_messages(self, session_id: str) -> tuple[str, list[dict[str, Any]]]:
        return await self.client.get_messages(session_id)

    async def list_models(self) -> list[ModelItem]:
        return await self.client.list_models()

    async def send_message_stream(self, session_id: str, content: str) -> AsyncIterator[RuntimeTransportEvent]:
        async for payload in self.client.stream_message(session_id, content):
            yield normalize_runtime_event(payload, source=self.mode, session_id=session_id)

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        await self.client.interrupt(session_id, keep_queue=keep_queue)

    async def steer(self, session_id: str, text: str) -> int:
        return await self.client.steer(session_id, text)

    async def command_complete(self, prefix: str, *, session_id: str = "") -> list[str]:
        return await self.client.slash_complete(prefix, session_id=session_id)

    async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict[str, Any]:
        return await self.client.command_dispatch(name, arg, session_id=session_id)

    async def list_skills(self) -> list[RegistryItem]:
        return await self.client.list_skills()

    async def list_plugins(self) -> list[RegistryItem]:
        return await self.client.list_plugins()

    async def get_tui_config(self) -> TuiConfig:
        return await self.client.get_tui_config()

    async def slash_exec(self, command: str, *, session_id: str = "") -> dict[str, Any]:
        return await self.client.slash_exec(command, session_id=session_id)

    async def respond_approval(self, session_id: str, approval_id: str, decision: str) -> None:
        await self.client.respond_approval(session_id, approval_id, decision)

    async def respond_clarify(self, session_id: str, clarify_id: str, answer: str) -> None:
        await self.client.respond_clarify(session_id, clarify_id, answer)

    async def transcribe_audio(self, data_url: str, *, mime_type: str = "audio/wav") -> str:
        return await self.client.transcribe_audio(data_url, mime_type=mime_type)


__all__ = ["HttpRuntimeTransport"]
