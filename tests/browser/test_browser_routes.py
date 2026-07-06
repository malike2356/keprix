"""Browser route tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_browser_session_requires_approval(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/browser/session",
            headers=headers,
            json={"objective": "Search the site", "url": "https://example.com"},
        )
        assert created.status_code == 200
        session_id = created.json()["session_id"]

        pending = await client.post(
            f"/api/browser/{session_id}/run",
            headers=headers,
            json={"action": "submit", "selector": "submit"},
        )
        assert pending.status_code == 200
        assert pending.json()["status"] == "awaiting_approval"

        approved = await client.post(f"/api/browser/{session_id}/approve", headers=headers)
        assert approved.status_code == 200
        assert approved.json()["status"] == "executed"

        actions = await client.get(f"/api/browser/{session_id}/actions", headers=headers)
        assert actions.status_code == 200
        assert len(actions.json()["actions"]) >= 2

        proposals = await client.get(f"/api/browser/{session_id}/proposals", headers=headers)
        assert proposals.status_code == 200
        assert proposals.json()["proposals"]


@pytest.mark.asyncio
async def test_browser_qa_run_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    scenario = "Given I open https://example.com\nThen I take a screenshot"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/browser/qa/run",
            headers=headers,
            json={"scenario": scenario, "url": "about:blank"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["passed"] is True
        assert body["session_id"]
