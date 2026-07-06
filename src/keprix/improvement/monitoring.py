"""Monitoring metrics for agent platform interfaces and improvement loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.improvement.run_analyzer import RunAnalyzer, _runs_dir


@dataclass
class PlatformMetrics:
    run_success_rate: float = 0.0
    tool_failure_rate: float = 0.0
    user_satisfaction: float = 0.0
    cost_by_agent: dict[str, float] = field(default_factory=dict)
    latency_by_tool: dict[str, float] = field(default_factory=dict)
    improvement_proposals: int = 0


def collect_metrics(*, agent_id: str | None = None) -> PlatformMetrics:
    analyzer = RunAnalyzer()
    runs = []
    runs_dir = _runs_dir()
    import json

    for path in runs_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if agent_id and data.get("agent_id") != agent_id:
            continue
        runs.append(data)

    if not runs:
        proposals = analyzer.list_proposals()
        return PlatformMetrics(improvement_proposals=len(proposals))

    ok_count = sum(1 for run in runs if run.get("ok"))
    tool_calls = [call for run in runs for call in run.get("tool_calls", [])]
    failed_tools = [call for call in tool_calls if not call.get("ok", True)]
    satisfaction_scores = [run.get("metadata", {}).get("satisfaction") for run in runs if run.get("metadata", {}).get("satisfaction") is not None]

    cost_by_agent: dict[str, float] = {}
    latency_by_tool: dict[str, list[float]] = {}
    for run in runs:
        aid = str(run.get("agent_id", "unknown"))
        cost_by_agent[aid] = cost_by_agent.get(aid, 0.0) + float(run.get("cost_usd", 0.0))
        for call in run.get("tool_calls", []):
            name = str(call.get("name", "unknown"))
            latency_by_tool.setdefault(name, []).append(float(call.get("duration_ms", 0)))

    return PlatformMetrics(
        run_success_rate=ok_count / len(runs),
        tool_failure_rate=(len(failed_tools) / len(tool_calls)) if tool_calls else 0.0,
        user_satisfaction=(sum(satisfaction_scores) / len(satisfaction_scores)) if satisfaction_scores else 0.0,
        cost_by_agent=cost_by_agent,
        latency_by_tool={name: sum(values) / len(values) for name, values in latency_by_tool.items()},
        improvement_proposals=len(analyzer.list_proposals()),
    )


def metrics_to_dict(metrics: PlatformMetrics) -> dict[str, Any]:
    return {
        "run_success_rate": metrics.run_success_rate,
        "tool_failure_rate": metrics.tool_failure_rate,
        "user_satisfaction": metrics.user_satisfaction,
        "cost_by_agent": metrics.cost_by_agent,
        "latency_by_tool": metrics.latency_by_tool,
        "improvement_proposals": metrics.improvement_proposals,
    }
