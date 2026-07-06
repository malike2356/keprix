"""Research task ID validation tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_invalid_task_id_returns_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/research/tasks/not-a-valid-id")
    assert response.status_code == 422
    payload = response.json()
    detail = payload.get("detail") or payload.get("error", "")
    assert "Invalid task ID format" in str(detail)
