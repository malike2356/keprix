"""Guardrail tests for agents runtime."""

from __future__ import annotations

import pytest

from keprix.agents_runtime.agent_spec import AgentSpec
from keprix.agents_runtime.executor import run_agent_step, start_run
from keprix.agents_runtime.guardrail import run_guardrails
from keprix.agents_runtime.run_context import get_run, reset_runs


@pytest.fixture(autouse=True)
def _clean_runs():
    reset_runs()
    yield
    reset_runs()


def test_secret_leakage_blocks_output() -> None:
    spec = AgentSpec(name="test", instructions="x", guardrails=["secret_leakage"])
    result = run_guardrails("token sk-abcdefghijklmnopqrstuvwxyz12", spec, phase="output")
    assert not result.passed
    assert result.guardrail == "secret_leakage"


def test_financial_action_requires_approval() -> None:
    spec = AgentSpec(name="billing_agent", instructions="x", guardrails=["financial_action"])
    result = run_guardrails("I will process a refund now", spec, phase="output", context={})
    assert not result.passed
    assert result.guardrail == "financial_action"


@pytest.mark.asyncio
async def test_risky_output_blocked_for_repair() -> None:
    started = await start_run("billing_agent", user_input="Please review my account status")
    run_id = started["run_id"]
    ctx = get_run(run_id)
    assert ctx is not None

    blocked = await run_agent_step(
        ctx,
        user_input="Please review my account status",
        draft_output="I will issue a refund to your credit card immediately",
    )
    assert blocked["status"] == "repair"
    assert blocked["guardrail"] == "financial_action"
    assert blocked["repair_hint"]

    guardrail_events = [e for e in ctx.trace if e.type == "guardrail"]
    assert len(guardrail_events) == 1

    repaired = await run_agent_step(
        ctx,
        user_input="Please review my account status",
        draft_output='{"resolution": "Escalated to human for account review"}',
    )
    assert repaired["status"] == "ok"
