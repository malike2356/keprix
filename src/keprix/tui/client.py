"""HTTP client for the Keprix chat TUI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:3333"


class SessionNotFoundError(Exception):
    """Raised when a conversation no longer exists on the backend."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


@dataclass
class SessionItem:
    id: str
    title: str
    preview: str = ""
    last_active: str = ""
    parent_id: str = ""
    related_ids: list[str] = field(default_factory=list)
    pinned: bool = False
    resumed_from: str = ""
    forked_from: str = ""
    search_match: str = ""


@dataclass
class ModelItem:
    id: str
    provider: str
    name: str
    context_window: int = 0
    pricing_input: float = 0.0
    pricing_output: float = 0.0


@dataclass
class RegistryItem:
    name: str
    description: str = ""
    installed: bool = True
    enabled: bool = True
    source: str = ""
    version: str = ""


@dataclass
class TurnStatus:
    busy: bool
    mode: str
    queue_depth: int
    partial_chars: int


@dataclass
class TuiConfig:
    busy_input_mode: str
    busy_input_modes: list[str]
    details_modes: dict[str, str]
    compose_key: str
    voice_record_key: str
    voice_enabled: bool


class SteerNotBusyError(Exception):
    """Raised when steer is requested but the session has no active agent turn."""


class KeprixClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("KEPRIX_API_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.token = token or os.environ.get("KEPRIX_API_TOKEN")
        self.model = model or os.environ.get("KEPRIX_DEFAULT_MODEL")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/health")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def ensure_auth(self) -> None:
        if self.token:
            return
        username = (
            os.environ.get("KEPRIX_ADMIN_USERNAME")
            or os.environ.get("KEPRIX_ADMIN_EMAIL")
            or "admin"
        )
        password = os.environ.get("KEPRIX_ADMIN_PASSWORD", "")
        if not password:
            return
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/auth/login",
                headers={"Content-Type": "application/json"},
                json={"username": username, "password": password},
            )
            if response.status_code == 200:
                token = response.json().get("token")
                if token:
                    self.token = str(token)

    async def session_exists(self, session_id: str) -> bool:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/conversations/{session_id}",
                headers=self._headers(),
            )
            return response.status_code == 200

    async def ensure_ready_session(self, session_id: str | None) -> str:
        await self.ensure_auth()
        if session_id and await self.session_exists(session_id):
            return session_id
        session = await self.create_session()
        return session.id

    async def list_sessions(self) -> list[SessionItem]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/conversations",
                headers=self._headers(),
                params={"limit": 50, "sort": "updated_at:desc"},
            )
            response.raise_for_status()
            payload = response.json()
        items = []
        for row in payload.get("items") or []:
            items.append(
                SessionItem(
                    id=str(row["id"]),
                    title=str(row.get("title") or "Conversation"),
                    preview=str(row.get("preview") or ""),
                    last_active=str(row.get("updated_at") or row.get("last_active") or ""),
                    parent_id=str(row.get("parent_id") or ""),
                    related_ids=[str(item) for item in row.get("related_ids") or []],
                    pinned=bool(row.get("pinned", False)),
                    resumed_from=str(row.get("resumed_from") or ""),
                    forked_from=str(row.get("forked_from") or ""),
                    search_match=str(row.get("search_match") or ""),
                )
            )
        return items

    async def create_session(self, title: str = "New conversation") -> SessionItem:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/conversations",
                headers=self._headers(),
                json={"title": title},
            )
            response.raise_for_status()
            row = response.json()
        return SessionItem(id=str(row["id"]), title=str(row.get("title") or title))

    async def delete_session(self, session_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self.base_url}/api/conversations/{session_id}",
                headers=self._headers(),
            )
            response.raise_for_status()

    async def get_messages(self, session_id: str) -> tuple[str, list[dict[str, Any]]]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/conversations/{session_id}",
                headers=self._headers(),
            )
            if response.status_code == 404:
                raise SessionNotFoundError(session_id)
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("title") or "Conversation"), list(payload.get("messages") or [])

    async def list_models(self) -> list[ModelItem]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/models/available",
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        models = []
        for row in payload.get("models") or []:
            models.append(
                ModelItem(
                    id=str(row["id"]),
                    provider=str(row.get("provider") or ""),
                    name=str(row.get("name") or row["id"]),
                    context_window=int(row.get("context_window") or row.get("context") or 0),
                    pricing_input=float(row.get("pricing_input") or row.get("input_price") or 0.0),
                    pricing_output=float(row.get("pricing_output") or row.get("output_price") or 0.0),
                )
            )
        return models

    async def list_skills(self) -> list[RegistryItem]:
        return await self._list_registry_items("/api/skills", "skills")

    async def list_plugins(self) -> list[RegistryItem]:
        return await self._list_registry_items("/api/plugins", "plugins")

    async def _list_registry_items(self, path: str, key: str) -> list[RegistryItem]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            payload = response.json()
        rows = payload.get(key) or payload.get("items") or []
        items: list[RegistryItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            items.append(
                RegistryItem(
                    name=str(row.get("name") or row.get("slug") or ""),
                    description=str(row.get("description") or ""),
                    installed=bool(row.get("installed", True)),
                    enabled=bool(row.get("enabled", True)),
                    source=str(row.get("source") or row.get("path") or ""),
                    version=str(row.get("version") or ""),
                )
            )
        return [item for item in items if item.name]

    async def stream_message(self, session_id: str, content: str) -> AsyncIterator[dict[str, Any]]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/conversations/{session_id}/messages",
                headers=self._headers(),
                json={"content": content, "file_ids": [], "model": self.model},
            ) as response:
                if response.status_code == 404:
                    raise SessionNotFoundError(session_id)
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    yield json.loads(line)

    async def get_turn_status(self, session_id: str) -> TurnStatus:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/conversations/{session_id}/turn-status",
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        return TurnStatus(
            busy=bool(payload.get("busy")),
            mode=str(payload.get("mode") or "interrupt"),
            queue_depth=int(payload.get("queue_depth") or 0),
            partial_chars=int(payload.get("partial_chars") or 0),
        )

    async def get_tui_config(self) -> TuiConfig:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/tui/config",
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        modes = payload.get("busy_input_modes") or ["interrupt", "queue", "steer"]
        details_raw = payload.get("details") or {}
        details_modes = (
            {str(k): str(v) for k, v in details_raw.items()}
            if isinstance(details_raw, dict)
            else {}
        )
        return TuiConfig(
            busy_input_mode=str(payload.get("busy_input_mode") or "interrupt"),
            busy_input_modes=[str(mode) for mode in modes],
            details_modes=details_modes,
            compose_key=str(payload.get("compose_key") or "ctrl+g"),
            voice_record_key=str(payload.get("voice_record_key") or "ctrl+b"),
            voice_enabled=bool(payload.get("voice_enabled", True)),
        )

    async def steer(self, session_id: str, text: str) -> int:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{session_id}/steer",
                headers=self._headers(),
                json={"text": text},
            )
            if response.status_code == 409:
                raise SteerNotBusyError(session_id)
            response.raise_for_status()
            payload = response.json()
        return int(payload.get("queued_chars") or len(text.strip()))

    async def interrupt(self, session_id: str, *, keep_queue: bool = False) -> None:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{session_id}/interrupt",
                headers=self._headers(),
                json={"keep_queue": keep_queue},
            )
            response.raise_for_status()

    async def respond_clarify(self, session_id: str, clarify_id: str, answer: str) -> None:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{session_id}/clarify/{clarify_id}/respond",
                headers=self._headers(),
                json={"answer": answer},
            )
            response.raise_for_status()

    async def respond_approval(self, session_id: str, approval_id: str, decision: str) -> None:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/conversations/{session_id}/approval/{approval_id}/respond",
                headers=self._headers(),
                json={"decision": decision},
            )
            response.raise_for_status()

    async def transcribe_audio(self, data_url: str, *, mime_type: str = "audio/wav") -> str:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/audio/transcribe",
                headers=self._headers(),
                json={"data_url": data_url, "mime_type": mime_type},
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("transcript") or "").strip()

    async def slash_exec(self, command: str, *, session_id: str = "") -> dict[str, Any]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/slash/exec",
                headers=self._headers(),
                json={"command": command, "session_id": session_id, "platform": "tui"},
            )
            response.raise_for_status()
            return response.json()

    async def slash_complete(self, prefix: str, *, session_id: str = "") -> list[str]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/api/slash/complete",
                headers=self._headers(),
                json={"prefix": prefix, "session_id": session_id},
            )
            response.raise_for_status()
            payload = response.json()
        rows = payload.get("candidates") or []
        return [str(item) for item in rows]

    async def fetch_setup_status(self) -> dict[str, Any]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/api/setup/status",
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {}

    async def save_minimal_setup(
        self,
        *,
        provider: str,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
    ) -> dict[str, Any]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/setup/minimal",
                headers=self._headers(),
                json={
                    "provider": provider,
                    "api_key": api_key,
                    "base_url": base_url,
                    "model": model,
                },
            )
            if response.status_code >= 400:
                detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else response.text
                raise RuntimeError(str(detail or response.text))
            return response.json()

    async def command_dispatch(self, name: str, arg: str, *, session_id: str = "") -> dict[str, Any]:
        await self.ensure_auth()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/command/dispatch",
                headers=self._headers(),
                json={"name": name, "arg": arg, "session_id": session_id},
            )
            response.raise_for_status()
            return response.json()
