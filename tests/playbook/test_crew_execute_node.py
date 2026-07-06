"""Tests for crew_execute playbook node (Prompt 195)."""

from __future__ import annotations

import pytest

from keprix.playbook.sdk_workflow import start_workflow_run
from keprix.teams.registry import team_registry
from keprix.teams.yaml_loader import crew_from_yaml

SAMPLE_CREW_YAML = """
name: sample-crew
roles:
  builder:
    goal: Build features
    backstory: Senior engineer
tasks:
  build:
    description: Implement the requested change
    role: builder
    expected_output: result.json
flow:
  start: build
"""


@pytest.fixture
def registered_sample_crew():
    crew, flow = crew_from_yaml(SAMPLE_CREW_YAML)
    team_registry.register(crew, flow)
    yield crew.name


@pytest.mark.asyncio
async def test_crew_flow_playbook_completes(registered_sample_crew: str) -> None:
    run = await start_workflow_run(
        {
            "graph_id": "crew-flow-test",
            "entry": "execute",
            "steps": [
                {
                    "id": "execute",
                    "type": "crew_execute",
                    "config": {
                        "team_id": registered_sample_crew,
                        "objective": "Ship playbook crew node",
                    },
                },
            ],
            "edges": [],
        },
        workspace_id="default",
        initial_state={},
    )
    assert run.status.value == "completed"
    assert "crew_result" in run.state
    assert run.state["crew_result"]["team_id"] == registered_sample_crew
    assert "build" in run.state["crew_result"]["task_results"]
