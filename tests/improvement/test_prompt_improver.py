"""Tests for prompt improver."""

from __future__ import annotations

from keprix.improvement.prompt_improver import propose_prompt_improvements
from keprix.improvement.run_analyzer import ImprovementProposal, RunRecord


def test_prompt_improver_suggests_guardrails_after_failure() -> None:
    record = RunRecord(
        run_id="run-1",
        agent_id="demo-agent",
        ok=False,
        metadata={"system_prompt": "You are a helpful agent."},
    )
    proposals = [
        ImprovementProposal(
            proposal_id="prop-1",
            run_id="run-1",
            agent_id="demo-agent",
            category="repeated_failure",
            title="Run failed",
            detail="Step 3 failed",
        )
    ]
    improvements = propose_prompt_improvements(record, proposals)
    assert improvements
    assert "alternate approach" in improvements[0].suggested_prompt


def test_prompt_improver_handles_user_correction() -> None:
    record = RunRecord(
        run_id="run-2",
        agent_id="demo-agent",
        ok=True,
        metadata={"system_prompt": "You are a helpful agent."},
    )
    proposals = [
        ImprovementProposal(
            proposal_id="prop-2",
            run_id="run-2",
            agent_id="demo-agent",
            category="user_correction",
            title="User corrections recorded",
            detail="Use UTC timestamps",
        )
    ]
    improvements = propose_prompt_improvements(record, proposals)
    assert "correction" in improvements[0].suggested_prompt.lower()
