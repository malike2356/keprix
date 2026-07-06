"""Agent specification for the multi-agent runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ApprovalPolicy = Literal["auto", "human", "tool_risky"]


@dataclass
class AgentSpec:
    name: str
    instructions: str
    tools: list[str] = field(default_factory=list)
    output_schema: dict[str, Any] | None = None
    handoffs: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    model_profile: str = "default"
    memory_scope: str = "session"
    approval_policy: ApprovalPolicy = "auto"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "instructions": self.instructions,
            "tools": list(self.tools),
            "output_schema": self.output_schema,
            "handoffs": list(self.handoffs),
            "guardrails": list(self.guardrails),
            "model_profile": self.model_profile,
            "memory_scope": self.memory_scope,
            "approval_policy": self.approval_policy,
        }


DEFAULT_AGENTS: dict[str, AgentSpec] = {
    "support_agent": AgentSpec(
        name="support_agent",
        instructions="Answer support questions and route billing issues to billing_agent.",
        tools=["search_docs", "create_ticket"],
        handoffs=["billing_agent", "human_reviewer"],
        guardrails=["secret_leakage", "output_schema"],
        output_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
    ),
    "billing_agent": AgentSpec(
        name="billing_agent",
        instructions="Handle subscription and invoice questions.",
        tools=["lookup_invoice", "apply_credit"],
        guardrails=["secret_leakage", "financial_action", "output_schema"],
        approval_policy="human",
        output_schema={"type": "object", "properties": {"resolution": {"type": "string"}}},
    ),
}


def get_agent(name: str) -> AgentSpec | None:
    return DEFAULT_AGENTS.get(name)


def list_agents() -> list[AgentSpec]:
    return list(DEFAULT_AGENTS.values())
