"""Analytics Must: session titles, datasets, run stdout with auto_repair."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app


@pytest.mark.asyncio
async def test_create_rename_session_title(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/api/analytics/sessions",
            headers=headers,
            json={"title": "Sales Q1"},
        )
        assert created.status_code == 200
        body = created.json()
        assert body["title"] == "Sales Q1"
        session_id = body["session_id"]

        renamed = await client.patch(
            f"/api/analytics/sessions/{session_id}",
            headers=headers,
            json={"title": "Sales Q1 renamed"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["title"] == "Sales Q1 renamed"

        listed = await client.get("/api/analytics/sessions", headers=headers)
        assert listed.status_code == 200
        match = next(item for item in listed.json()["sessions"] if item["session_id"] == session_id)
        assert match["title"] == "Sales Q1 renamed"


@pytest.mark.asyncio
async def test_dataset_library_crud(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}
    payload = {"name": "demo", "data": "a,b\n1,2\n", "source_filename": "demo.csv"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        saved = await client.post("/api/analytics/datasets", headers=headers, json=payload)
        assert saved.status_code == 200
        dataset_id = saved.json()["dataset_id"]
        assert saved.json()["name"] == "demo"

        listed = await client.get("/api/analytics/datasets", headers=headers)
        assert listed.status_code == 200
        assert any(item["dataset_id"] == dataset_id for item in listed.json()["datasets"])

        loaded = await client.get(f"/api/analytics/datasets/{dataset_id}", headers=headers)
        assert loaded.status_code == 200
        assert "1,2" in loaded.json()["data"]

        deleted = await client.delete(f"/api/analytics/datasets/{dataset_id}", headers=headers)
        assert deleted.status_code == 200
        missing = await client.get(f"/api/analytics/datasets/{dataset_id}", headers=headers)
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_run_auto_repair_returns_stdout(monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_API_TOKEN", "test-api-token")
    headers = {"Authorization": "Bearer test-api-token"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/analytics/sessions", headers=headers, json={"title": "Run"})
        session_id = created.json()["session_id"]
        run = await client.post(
            f"/api/analytics/sessions/{session_id}/run",
            headers=headers,
            json={"code": "print('hello-analytics')", "auto_repair": True},
        )
        assert run.status_code == 200
        body = run.json()
        assert body["ok"] is True
        assert "hello-analytics" in (body.get("stdout") or "")
