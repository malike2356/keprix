"""Tests for crew run event store (Prompt 195)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.teams.registry import team_registry
from keprix.teams.run_store import team_run_store
from keprix.teams.yaml_loader import crew_from_yaml

SAMPLE_YAML = """
name: event-crew
roles:
  builder:
    goal: Build
    backstory: Engineer
tasks:
  build:
    description: Build task
    role: builder
flow:
  start: build
"""


@pytest.fixture
def registered_event_crew():
    team_run_store._runs.clear()
    crew, flow = crew_from_yaml(SAMPLE_YAML)
    team_registry.register(crew, flow)
    return crew.name


@pytest.mark.asyncio
async def test_team_run_records_events(registered_event_crew: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/teams/{registered_event_crew}/run",
            json={"objective": "Record crew events"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"]
    assert body["workspace_url"].startswith("/admin/teams")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        events_resp = await client.get(
            f"/api/teams/{registered_event_crew}/runs/{body['run_id']}/events",
        )
    assert events_resp.status_code == 200
    events = events_resp.json()["events"]
    assert len(events) >= 2
    assert any(event["event_type"] == "before_task" for event in events)
    assert any(event["event_type"] == "after_task" for event in events)
