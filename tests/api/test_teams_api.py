"""Tests for teams HTTP API."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from tests.teams.test_yaml_loader import MINIMAL_YAML


@pytest.mark.asyncio
async def test_import_and_list_team() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        imported = await client.post("/api/teams/import", json={"yaml": MINIMAL_YAML})
        assert imported.status_code == 200
        assert imported.json()["name"] == "test-crew"
        listed = await client.get("/api/teams")
        assert listed.status_code == 200
        assert "test-crew" in listed.json()["teams"]


@pytest.mark.asyncio
async def test_run_team_returns_state() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/teams/import", json={"yaml": MINIMAL_YAML})
        response = await client.post(
            "/api/teams/test-crew/run",
            json={"objective": "Ship the feature"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["name"] == "test-crew"
        assert "state" in payload
