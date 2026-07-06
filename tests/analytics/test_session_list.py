"""Analytics session list API tests (Prompt 197)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_analytics_session_list(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/analytics/sessions", headers=headers)
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        listed = await client.get("/api/analytics/sessions", headers=headers)
        assert listed.status_code == 200
        sessions = listed.json()["sessions"]
        assert any(item["session_id"] == session_id for item in sessions)

        loaded = await client.get(f"/api/analytics/sessions/{session_id}", headers=headers)
        assert loaded.status_code == 200
        assert loaded.json()["session_id"] == session_id
