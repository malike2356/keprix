"""Tests for YAML import and export of crew definitions."""

from __future__ import annotations

import pytest

from keprix.teams.yaml_loader import crew_from_yaml, crew_to_yaml


MINIMAL_YAML = """
name: test-crew
roles:
  builder:
    goal: Build things
    backstory: Senior engineer
tasks:
  task_one:
    description: Do the first task
    role: builder
    expected_output: result.json
flow:
  start: task_one
"""

MULTI_TASK_YAML = """
name: pipeline
roles:
  analyst:
    goal: Analyse data
    backstory: Data expert
  writer:
    goal: Write reports
    backstory: Report writer
tasks:
  analyse:
    description: Analyse the dataset
    role: analyst
    expected_output: analysis.json
  report:
    description: Write the final report
    role: writer
    dependencies:
      - analyse
    human_review: true
    risk_level: medium
flow:
  start: analyse
"""


def test_crew_from_yaml_parses_name() -> None:
    crew, flow = crew_from_yaml(MINIMAL_YAML)
    assert crew.name == "test-crew"


def test_crew_from_yaml_parses_roles() -> None:
    crew, _ = crew_from_yaml(MINIMAL_YAML)
    assert "builder" in crew.roles
    assert crew.roles["builder"].goal == "Build things"


def test_crew_from_yaml_parses_tasks() -> None:
    crew, _ = crew_from_yaml(MINIMAL_YAML)
    assert len(crew.tasks) == 1
    assert crew.tasks[0].id == "task_one"
    assert crew.tasks[0].role == "builder"


def test_crew_from_yaml_parses_flow_start() -> None:
    _, flow = crew_from_yaml(MINIMAL_YAML)
    assert flow.start == "task_one"


def test_crew_from_yaml_parses_dependencies() -> None:
    crew, _ = crew_from_yaml(MULTI_TASK_YAML)
    report_task = next(t for t in crew.tasks if t.id == "report")
    assert "analyse" in report_task.dependencies


def test_crew_from_yaml_parses_human_review() -> None:
    crew, _ = crew_from_yaml(MULTI_TASK_YAML)
    report_task = next(t for t in crew.tasks if t.id == "report")
    assert report_task.human_review is True
    assert report_task.risk_level == "medium"


def test_crew_to_yaml_round_trips() -> None:
    crew, flow = crew_from_yaml(MINIMAL_YAML)
    dumped = crew_to_yaml(crew, flow)
    crew2, flow2 = crew_from_yaml(dumped)

    assert crew2.name == crew.name
    assert flow2.start == flow.start
    assert len(crew2.tasks) == len(crew.tasks)
    assert crew2.tasks[0].id == crew.tasks[0].id


def test_empty_yaml_produces_empty_crew() -> None:
    crew, flow = crew_from_yaml("")
    assert crew.name == "team"
    assert crew.tasks == []
