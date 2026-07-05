"""Keprix team orchestration primitives."""

from keprix.teams.agent_role import AgentRole, DEFAULT_ROLES, get_default_role
from keprix.teams.crew import Crew, CrewError
from keprix.teams.flow import TeamFlow
from keprix.teams.guardrails import GuardrailResult, run_guardrails
from keprix.teams.hooks import HookEvent, HookManager
from keprix.teams.registry import RegisteredTeam, TeamRegistry, team_registry
from keprix.teams.structured_output import StructuredOutputError, validate_structured_output
from keprix.teams.task import RetryPolicy, TaskResult, TeamTask
from keprix.teams.yaml_loader import crew_from_yaml, crew_to_yaml

__all__ = [
    "AgentRole",
    "Crew",
    "CrewError",
    "DEFAULT_ROLES",
    "GuardrailResult",
    "HookEvent",
    "HookManager",
    "RegisteredTeam",
    "RetryPolicy",
    "StructuredOutputError",
    "TaskResult",
    "TeamFlow",
    "TeamRegistry",
    "TeamTask",
    "crew_from_yaml",
    "crew_to_yaml",
    "get_default_role",
    "run_guardrails",
    "team_registry",
    "validate_structured_output",
]
