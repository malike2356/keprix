"""Cron API route tests."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.fixture(autouse=True)
def _auth_disabled(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")


@pytest.mark.asyncio
async def test_list_cron_jobs_route():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/cron/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_cron_job_route(monkeypatch, tmp_path):
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/cron/jobs",
            json={
                "name": "Morning brief",
                "schedule": "every 1h",
                "prompt": "Summarize overnight inbox items.",
            },
        )
        if response.status_code != 200:
            pytest.fail(response.text)
        body = response.json()
        assert body["name"] == "Morning brief"
        job_id = body["id"]

        listed = await client.get("/api/cron/jobs")
        assert any(item["id"] == job_id for item in listed.json())

        deleted = await client.delete(f"/api/cron/jobs/{job_id}")
        assert deleted.status_code == 200
