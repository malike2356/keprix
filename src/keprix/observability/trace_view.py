"""Trace view builder for agent runtime UI."""

from __future__ import annotations

from typing import Any

from keprix.agents_runtime.run_context import RunContext


def build_trace_view(ctx: RunContext) -> dict[str, Any]:
    events = ctx.trace_dict()
    return {
        "run_id": ctx.run_id,
        "current_agent": ctx.current_agent,
        "accepted_handoffs": list(ctx.accepted_handoffs),
        "events": events,
        "summary": {
            "agent_events": sum(1 for e in events if e["type"] in {"agent_start", "agent_end"}),
            "handoffs": sum(1 for e in events if e["type"] == "handoff"),
            "guardrails": sum(1 for e in events if e["type"] == "guardrail"),
            "tools": sum(1 for e in events if e["type"] == "tool"),
            "outputs": sum(1 for e in events if e["type"] == "output"),
        },
    }
