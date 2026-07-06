"""Eval metrics aggregation (Prompt 57)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from keprix.backend.evals.benchmark import BenchmarkRunResult


@dataclass
class EvalMetrics:
    total_tasks: int = 0
    passed_tasks: int = 0
    pass_rate: float = 0.0
    total_cost_usd: float = 0.0
    avg_cost_usd: float = 0.0
    avg_runtime_ms: float = 0.0
    safety_warning_count: int = 0
    failure_count: int = 0
    by_workflow: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_tasks": self.total_tasks,
            "passed_tasks": self.passed_tasks,
            "pass_rate": self.pass_rate,
            "total_cost_usd": self.total_cost_usd,
            "avg_cost_usd": self.avg_cost_usd,
            "avg_runtime_ms": self.avg_runtime_ms,
            "safety_warning_count": self.safety_warning_count,
            "failure_count": self.failure_count,
            "by_workflow": self.by_workflow,
        }


def aggregate_metrics(results: list[BenchmarkRunResult]) -> EvalMetrics:
    total_tasks = sum(result.total for result in results)
    passed_tasks = sum(result.passed for result in results)
    total_cost = sum(result.avg_cost_usd * result.total for result in results)
    total_runtime = sum(result.avg_runtime_ms * result.total for result in results)
    safety_warnings = sum(len(result.safety_warnings) for result in results)
    failures = total_tasks - passed_tasks

    by_workflow: dict[str, dict[str, Any]] = {}
    for result in results:
        bucket = by_workflow.setdefault(
            result.workflow,
            {"suites": 0, "passed": 0, "total": 0, "pass_rate": 0.0},
        )
        bucket["suites"] += 1
        bucket["passed"] += result.passed
        bucket["total"] += result.total
        bucket["pass_rate"] = bucket["passed"] / bucket["total"] if bucket["total"] else 0.0

    return EvalMetrics(
        total_tasks=total_tasks,
        passed_tasks=passed_tasks,
        pass_rate=passed_tasks / total_tasks if total_tasks else 0.0,
        total_cost_usd=total_cost,
        avg_cost_usd=total_cost / total_tasks if total_tasks else 0.0,
        avg_runtime_ms=total_runtime / total_tasks if total_tasks else 0.0,
        safety_warning_count=safety_warnings,
        failure_count=failures,
        by_workflow=by_workflow,
    )
