"""Agent role model for Keprix teams."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentRole:
    name: str
    goal: str
    backstory: str = ""
    tools: list[str] = field(default_factory=list)
    llm_profile: str = "default"
    memory_scope: str = "workspace"
    guardrails: list[str] = field(default_factory=list)
    delegation_policy: str = "none"
    approval_policy: str = "risk_based"
    max_iterations: int = 3
    structured_output_schema: dict[str, Any] | None = None

    def can_delegate(self) -> bool:
        return self.delegation_policy in {"allowed", "required"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "goal": self.goal,
            "backstory": self.backstory,
            "tools": list(self.tools),
            "llm_profile": self.llm_profile,
            "memory_scope": self.memory_scope,
            "guardrails": list(self.guardrails),
            "delegation_policy": self.delegation_policy,
            "approval_policy": self.approval_policy,
            "max_iterations": self.max_iterations,
            "structured_output_schema": self.structured_output_schema,
        }


DEFAULT_ROLES: dict[str, AgentRole] = {
    "researcher": AgentRole(
        name="researcher",
        goal="Find relevant facts with sources.",
        backstory="Research specialist focused on evidence and source quality.",
        tools=["web_search", "rag_search"],
    ),
    "analyst": AgentRole(
        name="analyst",
        goal="Synthesize findings into decisions.",
        backstory="Analyst who compares evidence and produces clear recommendations.",
    ),
    "builder": AgentRole(
        name="builder",
        goal="Turn plans into working artifacts.",
        backstory="General builder for practical implementation work.",
        tools=["workspace_write"],
    ),
    "browser_operator": AgentRole(
        name="browser_operator",
        goal="Operate browser workflows safely.",
        backstory="Browser automation specialist.",
        tools=["browser"],
        approval_policy="always_for_external_write",
    ),
    "data_analyst": AgentRole(
        name="data_analyst",
        goal="Analyze datasets and produce reproducible outputs.",
        backstory="Data and statistics specialist.",
        tools=["python", "notebook"],
    ),
    "code_engineer": AgentRole(
        name="code_engineer",
        goal="Implement scoped code changes with tests.",
        backstory="Software engineer operating under repository policy.",
        tools=["repo_read", "repo_patch", "tests"],
    ),
    "qa_reviewer": AgentRole(
        name="qa_reviewer",
        goal="Check quality, regressions, and acceptance criteria.",
        backstory="Quality reviewer focused on evidence.",
    ),
    "compliance_reviewer": AgentRole(
        name="compliance_reviewer",
        goal="Check legal, policy, privacy, and governance requirements.",
        backstory="Compliance reviewer with conservative approval posture.",
        approval_policy="always",
    ),
    "launch_operator": AgentRole(
        name="launch_operator",
        goal="Coordinate release and launch tasks.",
        backstory="Launch specialist for publishing and operational handoff.",
        approval_policy="always_for_publish",
    ),
}


def get_default_role(name: str) -> AgentRole | None:
    return DEFAULT_ROLES.get(name)
