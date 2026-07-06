"""Output validation tests for typed agents."""

from __future__ import annotations

import pytest

from keprix.typed_agents.agent import SupportAnswer, create_support_agent
from keprix.typed_agents.approval import ApprovalAction, approval_required
from keprix.typed_agents.dependencies import build_support_dependencies
from keprix.typed_agents.output_validation import validate_artifact_metadata, validate_handoff_payload, validate_output
from keprix.typed_agents.schemas import AgentRunContext


@pytest.mark.asyncio
async def test_support_agent_validates_final_output() -> None:
    agent = create_support_agent()
    deps = build_support_dependencies()
    context = AgentRunContext()
    result = await agent.run(
        deps=deps,
        context=context,
        tool_calls=[{"name": "lookup_ticket", "arguments": {"ticket_id": "T-300"}}],
        raw_output={
            "ticket_id": "T-300",
            "resolution": "Password reset link sent",
            "cited_policy": "AUTH-01",
        },
        auto_approve=True,
    )
    assert isinstance(result.output, SupportAnswer)
    assert result.output.cited_policy == "AUTH-01"
    assert result.tool_calls


@pytest.mark.asyncio
async def test_invalid_output_triggers_repair_error() -> None:
    agent = create_support_agent()
    agent.retry_policy.max_attempts = 1
    deps = build_support_dependencies()
    context = AgentRunContext()
    with pytest.raises(ValueError, match="Final agent output failed validation"):
        await agent.finalize_output({"ticket_id": "only"}, deps, context=context, auto_approve=True)


def test_artifact_and_handoff_validation() -> None:
    artifact, artifact_error = validate_artifact_metadata(
        {
            "artifact_id": "art-1",
            "artifact_type": "report",
            "title": "Support summary",
            "trace_id": "trace-1",
        }
    )
    assert artifact is not None
    assert artifact_error is None

    handoff, handoff_error = validate_handoff_payload(
        {
            "target_agent": "FORGE",
            "reason": "Needs code change",
            "summary": "Patch auth middleware",
            "trace_id": "trace-2",
        }
    )
    assert handoff is not None
    assert handoff_error is None


def test_approval_hooks_cover_required_actions() -> None:
    assert approval_required(ApprovalAction.EMAIL_SEND) is True
    assert approval_required(ApprovalAction.BROWSER_SUBMIT) is True
    assert approval_required(ApprovalAction.FILE_WRITE) is True
    assert approval_required("payment_change") is True


def test_validate_output_accepts_model_instance() -> None:
    answer = SupportAnswer(ticket_id="T-1", resolution="Done", cited_policy="POL-1")
    validated, repair = validate_output(SupportAnswer, answer)
    assert repair is None
    assert validated == answer
