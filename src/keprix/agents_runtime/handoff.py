"""Controlled agent handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from keprix.agents_runtime.agent_spec import get_agent
from keprix.agents_runtime.run_context import RunContext

HandoffType = Literal["agent", "human", "tool", "playbook"]


@dataclass
class HandoffRecord:
    reason: str
    source: str
    target: str
    handoff_type: HandoffType
    context: dict[str, Any]
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "source": self.source,
            "target": self.target,
            "handoff_type": self.handoff_type,
            "context": self.context,
            "accepted": self.accepted,
        }


def execute_handoff(
    ctx: RunContext,
    *,
    target: str,
    reason: str,
    handoff_type: HandoffType = "agent",
    context: dict[str, Any] | None = None,
    accepted: bool | None = None,
) -> HandoffRecord:
    source = ctx.current_agent
    payload_context = dict(context or {})
    payload_context.update(ctx.state)

    if accepted is None:
        if handoff_type == "human":
            accepted = False
        elif handoff_type == "agent":
            spec = get_agent(source)
            accepted = target in (spec.handoffs if spec else [])
        else:
            accepted = True

    record = HandoffRecord(
        reason=reason,
        source=source,
        target=target,
        handoff_type=handoff_type,
        context=payload_context,
        accepted=accepted,
    )
    ctx.record(
        "handoff",
        source,
        {
            **record.to_dict(),
            "run_id": ctx.run_id,
        },
    )
    if accepted:
        ctx.current_agent = target
        ctx.accepted_handoffs.append(f"{source}->{target}")
        ctx.record("agent_start", target, {"handoff_from": source, "reason": reason})
    return record
