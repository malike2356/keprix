"""TUI streaming parser tests."""

from __future__ import annotations

import pytest

from keprix.tui.client import KeprixClient


@pytest.mark.asyncio
async def test_health_check_offline() -> None:
    client = KeprixClient(base_url="http://127.0.0.1:1")
    assert await client.health_check() is False
