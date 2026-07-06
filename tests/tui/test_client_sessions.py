"""TUI client session recovery tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.tui.client import KeprixClient, SessionNotFoundError


@pytest.mark.asyncio
async def test_ensure_ready_session_creates_when_missing() -> None:
    client = KeprixClient(base_url="http://127.0.0.1:3333")
    with patch.object(client, "session_exists", AsyncMock(return_value=False)):
        with patch.object(
            client,
            "create_session",
            AsyncMock(return_value=type("S", (), {"id": "new-session"})()),
        ):
            session_id = await client.ensure_ready_session("stale-session")
    assert session_id == "new-session"


@pytest.mark.asyncio
async def test_get_messages_raises_session_not_found() -> None:
    client = KeprixClient(base_url="http://127.0.0.1:3333")

    class _FakeResponse:
        status_code = 404

        def raise_for_status(self) -> None:
            return None

    class _FakeClient:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, *_args, **_kwargs):
            return _FakeResponse()

    with patch("httpx.AsyncClient", _FakeClient):
        with pytest.raises(SessionNotFoundError):
            await client.get_messages("missing")
