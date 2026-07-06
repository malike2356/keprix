"""HTTP client for the Keprix chat TUI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
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


@dataclass
class ModelItem:
    id: str
    provider: str
    name: str


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
                )
            )
        return models

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
