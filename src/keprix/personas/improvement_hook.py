"""Bridge persona runs into the auto-improvement loop (Prompt 71)."""

from __future__ import annotations

from typing import Any

from keprix.improvement.run_analyzer import ImprovementProposal, RunAnalyzer, RunRecord


def record_persona_run(
    *,
    run_id: str,
    agent_id: str,
    ok: bool,
    steps: list[dict[str, Any]] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    user_corrections: list[str] | None = None,
    eval_score: float | None = None,
    cost_usd: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> list[ImprovementProposal]:
    analyzer = RunAnalyzer()
    record = RunRecord(
        run_id=run_id,
        agent_id=agent_id,
        ok=ok,
        steps=steps or [],
        tool_calls=tool_calls or [],
        user_corrections=user_corrections or [],
        eval_score=eval_score,
        cost_usd=cost_usd,
        metadata=metadata or {},
    )
    analyzer.save_run(record)
    return analyzer.analyze(record)


def record_routing_outcome(
    *,
    run_id: str,
    primary_agent: str,
    matched_agents: list[str],
    message_count: int,
    metadata: dict[str, Any] | None = None,
) -> list[ImprovementProposal]:
    return record_persona_run(
        run_id=run_id,
        agent_id=primary_agent or "NEXUS",
        ok=message_count > 0,
        steps=[
            {
                "name": "nexus_route",
                "ok": message_count > 0,
                "matched_agents": matched_agents,
            }
        ],
        metadata=metadata or {},
    )
