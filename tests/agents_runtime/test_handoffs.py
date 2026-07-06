"""Handoff tests for agents runtime."""

from __future__ import annotations

import pytest

from keprix.agents_runtime.executor import handoff_run, run_agent_step, start_run
from keprix.agents_runtime.run_context import get_run, reset_runs
from keprix.observability.trace_export import export_trace
from keprix.observability.trace_view import build_trace_view


@pytest.fixture(autouse=True)
def _clean_runs():
    reset_runs()
    yield
    reset_runs()


@pytest.mark.asyncio
async def test_support_to_billing_handoff_trace_continuity() -> None:
    started = await start_run("support_agent", user_input="Customer asks about invoice #99")
    run_id = started["run_id"]
    assert started["status"] == "ok"

    ctx = get_run(run_id)
    assert ctx is not None
    ctx.record("tool", "support_agent", {"tool": "search_docs", "query": "invoice billing"})
    ctx.state["approved"] = True
    await handoff_run(run_id, target="billing_agent", reason="Billing question", accept=True)

    billing = await run_agent_step(
        ctx,
        user_input="Explain invoice #99",
        draft_output='{"resolution": "Invoice #99 is paid"}',
    )
    assert billing["status"] == "ok"
    assert billing["agent"] == "billing_agent"

    view = build_trace_view(ctx)
    types = [event["type"] for event in view["events"]]
    assert "agent_start" in types
    assert "handoff" in types
    assert "tool" in types
    assert "output" in types
    assert view["current_agent"] == "billing_agent"
    assert "support_agent->billing_agent" in view["accepted_handoffs"]

    exported = export_trace(ctx)
    assert exported["format"] == "keprix-agent-trace-v1"
    assert exported["run_id"] == run_id
