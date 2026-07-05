"""YAML import and export for Keprix teams."""

from __future__ import annotations

from typing import Any

import yaml

from keprix.teams.agent_role import AgentRole
from keprix.teams.crew import Crew
from keprix.teams.flow import TeamFlow
from keprix.teams.task import RetryPolicy, TeamTask


def crew_from_yaml(text: str) -> tuple[Crew, TeamFlow]:
    raw = yaml.safe_load(text) or {}
    roles = {
        role_id: AgentRole(
            name=role_id,
            goal=str(config.get("goal", "")),
            backstory=str(config.get("backstory", "")),
            tools=list(config.get("tools") or []),
            llm_profile=str(config.get("llm_profile", "default")),
            memory_scope=str(config.get("memory_scope", "workspace")),
            guardrails=list(config.get("guardrails") or []),
            delegation_policy=str(config.get("delegation_policy", "none")),
            approval_policy=str(config.get("approval_policy", "risk_based")),
            max_iterations=int(config.get("max_iterations", 3)),
            structured_output_schema=config.get("structured_output_schema"),
        )
        for role_id, config in dict(raw.get("roles") or {}).items()
    }
    tasks = [_task_from_yaml(task_id, config) for task_id, config in dict(raw.get("tasks") or {}).items()]
    flow_raw = dict(raw.get("flow") or {})
    flow = TeamFlow(
        name=str(raw.get("name", "team-flow")),
        start=str(flow_raw.get("start") or (tasks[0].id if tasks else "")),
        events={key: list(value or []) for key, value in dict(flow_raw.get("events") or {}).items()},
    )
    crew = Crew(name=str(raw.get("name", "team")), roles=roles, tasks=tasks)
    return crew, flow


def crew_to_yaml(crew: Crew, flow: TeamFlow) -> str:
    payload: dict[str, Any] = {
        "name": crew.name,
        "roles": {
            key: role.to_dict()
            for key, role in crew.roles.items()
            if key not in {"researcher", "analyst", "builder", "browser_operator", "data_analyst", "code_engineer", "qa_reviewer", "compliance_reviewer", "launch_operator"}
        },
        "tasks": {task.id: task.to_dict() for task in crew.tasks},
        "flow": {"start": flow.start, "events": dict(flow.events)},
    }
    return yaml.safe_dump(payload, sort_keys=False)


def _task_from_yaml(task_id: str, config: dict[str, Any]) -> TeamTask:
    retry = dict(config.get("retry_policy") or {})
    return TeamTask(
        id=task_id,
        description=str(config.get("description") or config.get("output") or task_id),
        expected_output=str(config.get("expected_output") or config.get("output") or ""),
        role=str(config.get("role", "builder")),
        dependencies=list(config.get("dependencies") or []),
        required_artifacts=list(config.get("required_artifacts") or []),
        output_schema=config.get("output_schema"),
        human_review=bool(config.get("human_review", False)),
        risk_level=str(config.get("risk_level", "low")),
        timeout_seconds=config.get("timeout"),
        retry_policy=RetryPolicy(
            max_attempts=int(retry.get("max_attempts", config.get("retries", 1))),
            retry_on_guardrail_failure=bool(retry.get("retry_on_guardrail_failure", True)),
        ),
        allow_delegation=bool(config.get("allow_delegation", False)),
        output_artifact=config.get("output_artifact") or config.get("output"),
    )
