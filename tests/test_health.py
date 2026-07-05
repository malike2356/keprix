"""Smoke test: health endpoint returns 200 with correct payload."""

import pytest
from httpx import AsyncClient, ASGITransport

from keprix.api.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["product"] == "Keprix"
    assert "version" in data
