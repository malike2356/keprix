"""Schema export tests for typed agents."""

from __future__ import annotations

from keprix.typed_agents.agent import SupportAnswer, create_support_agent
from keprix.typed_agents.dependencies import SupportDependencies
from keprix.typed_agents.schemas import AgentRunContext


def test_support_agent_exports_schemas() -> None:
    agent = create_support_agent()
    exported = agent.export_schemas(AgentRunContext(workspace_id="ws-1", user_id="user-1"))
    assert exported["agent_name"] == "support-agent"
    assert exported["output_schema"]["title"] == "SupportAnswer"
    assert exported["dependencies_schema"]["title"] == "SupportDependencies"
    assert len(exported["tools"]) == 1
    assert exported["tools"][0]["name"] == "lookup_ticket"
    assert "ticket_id" in exported["tools"][0]["input_schema"]["properties"]


def test_support_answer_model_shape() -> None:
    answer = SupportAnswer(ticket_id="T-100", resolution="Reset password", cited_policy="AUTH-01")
    assert answer.ticket_id == "T-100"
