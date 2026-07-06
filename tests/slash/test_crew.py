"""Slash /crew command tests (Prompt 195)."""

from __future__ import annotations

import pytest

from keprix.slash.commands.crew import handle_crew_slash
from keprix.slash.schemas import SlashContext
from keprix.teams.registry import team_registry
from keprix.teams.run_store import team_run_store
from keprix.teams.yaml_loader import crew_from_yaml

SAMPLE_YAML = """
name: slash-crew
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
def slash_crew():
    team_run_store._runs.clear()
    crew, flow = crew_from_yaml(SAMPLE_YAML)
    team_registry.register(crew, flow)
    return crew.name


@pytest.mark.asyncio
async def test_crew_slash_returns_workspace_url(slash_crew: str) -> None:
    ctx = SlashContext(
        raw_text=f'/crew {slash_crew} "Ship slash path"',
        command="crew",
        args=[slash_crew, "Ship", "slash", "path"],
        user_id="tester",
        workspace_id="default",
        channel="webchat",
        channel_user_id="tester",
        role="operator",
        request_id="req-1",
        metadata={},
    )
    result = await handle_crew_slash(ctx)
    assert result.ok is True
    assert "/admin/teams" in (result.message or "")
    assert result.data.get("run_id")
