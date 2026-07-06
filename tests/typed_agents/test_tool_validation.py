"""Tool validation tests for typed agents."""

from __future__ import annotations

import pytest

from keprix.typed_agents.agent import LookupTicketInput, create_support_agent
from keprix.typed_agents.dependencies import build_support_dependencies
from keprix.typed_agents.retries import RetryPolicy
from keprix.typed_agents.schemas import AgentRunContext
from keprix.typed_agents.tool_validation import validate_tool_arguments


@pytest.mark.asyncio
async def test_invalid_tool_args_return_repair_message() -> None:
    repair_args, repair = validate_tool_arguments("lookup_ticket", LookupTicketInput, {"ticket_id": "x"})
    assert repair_args is None
    assert repair is not None
    assert repair.kind == "tool_arguments"
    assert "ticket_id" in repair.to_prompt_block()


@pytest.mark.asyncio
async def test_repair_then_valid_tool_call_succeeds() -> None:
    agent = create_support_agent()
    agent.retry_policy = RetryPolicy(max_attempts=3)
    deps = build_support_dependencies()
    context = AgentRunContext()

    failed = await agent.invoke_tool("lookup_ticket", {"ticket_id": "x"}, deps, context=context, auto_approve=True)
    assert failed["ok"] is False
    assert failed["repair"].kind == "tool_arguments"

    ok = await agent.invoke_tool(
        "lookup_ticket",
        {"ticket_id": "T-200"},
        deps,
        context=context,
        auto_approve=True,
    )
    assert ok["ok"] is True
    assert ok["result"]["ticket_id"] == "T-200"


@pytest.mark.asyncio
async def test_unknown_tool_rejected() -> None:
    agent = create_support_agent()
    deps = build_support_dependencies()
    context = AgentRunContext()
    response = await agent.invoke_tool("missing_tool", {}, deps, context=context, auto_approve=True)
    assert response["ok"] is False
    assert "Unknown tool" in response["repair"].message
