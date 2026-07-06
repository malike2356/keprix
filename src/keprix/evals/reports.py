"""Eval reports and release gate."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.evals.cost import detect_cost_regression
from keprix.evals.latency import detect_latency_regression
from keprix.evals.registry import EvalSuite
from keprix.evals.runner import SuiteResult


@dataclass
class ReleaseGateResult:
    passed: bool
    pass_rate: float
    min_pass_rate: float
    cost_regression: bool
    latency_regression: bool
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "min_pass_rate": self.min_pass_rate,
            "cost_regression": self.cost_regression,
            "latency_regression": self.latency_regression,
            "failures": self.failures,
        }


def aggregate_pass_rate(results: list[SuiteResult]) -> float:
    passed = sum(result.passed for result in results)
    total = sum(result.total for result in results)
    return passed / total if total else 0.0


def evaluate_release_gate(
    results: list[SuiteResult],
    *,
    min_pass_rate: float = 0.9,
    baseline: dict[str, Any] | None = None,
    suites: list[EvalSuite] | None = None,
) -> ReleaseGateResult:
    failures: list[str] = []
    pass_rate = aggregate_pass_rate(results)
    if pass_rate < min_pass_rate:
        failures.append(f"Pass rate {pass_rate:.2%} below threshold {min_pass_rate:.2%}")

    for result in results:
        suite_min = min_pass_rate
        if suites:
            matching = next((suite for suite in suites if suite.name == result.suite), None)
            if matching:
                suite_min = matching.min_pass_rate
        if result.pass_rate < suite_min:
            failures.append(f"Suite {result.suite} pass rate {result.pass_rate:.2%} below {suite_min:.2%}")
        for task in result.tasks:
            if not task.passed and task.reason:
                failures.append(f"{result.suite}/{task.task_id}: {task.reason}")

    baseline = baseline or {}
    current_cost = sum(result.avg_cost_usd for result in results) / len(results) if results else 0.0
    current_latency = sum(result.avg_latency_ms for result in results) / len(results) if results else 0.0
    cost_check = detect_cost_regression(current_cost, float(baseline.get("avg_cost_usd", 0.0)))
    latency_check = detect_latency_regression(
        current_latency,
        float(baseline.get("avg_latency_ms", 0.0)),
    )
    if cost_check.detected:
        failures.append(cost_check.message)
    if latency_check.detected:
        failures.append(latency_check.message)

    return ReleaseGateResult(
        passed=len(failures) == 0,
        pass_rate=pass_rate,
        min_pass_rate=min_pass_rate,
        cost_regression=cost_check.detected,
        latency_regression=latency_check.detected,
        failures=failures,
    )


def render_markdown_report(results: list[SuiteResult], gate: ReleaseGateResult) -> str:
    lines = [
        "# Keprix Eval Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"Release gate: {'PASS' if gate.passed else 'FAIL'}",
        f"Overall pass rate: {gate.pass_rate:.2%}",
        "",
        "## Suites",
        "",
    ]
    for result in results:
        lines.append(f"### {result.suite} (v{result.version})")
        lines.append(f"- Category: {result.category}")
        lines.append(f"- Pass rate: {result.pass_rate:.2%} ({result.passed}/{result.total})")
        lines.append(f"- Avg cost: ${result.avg_cost_usd:.4f}")
        lines.append(f"- Avg latency: {result.avg_latency_ms:.1f} ms")
        lines.append("")
        for task in result.tasks:
            status = "PASS" if task.passed else "FAIL"
            lines.append(f"- {status} `{task.task_id}`")
            if task.reason:
                lines.append(f"  - Reason: {task.reason}")
        lines.append("")

    if gate.failures:
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in gate.failures)

    return "\n".join(lines)


def render_json_report(results: list[SuiteResult], gate: ReleaseGateResult) -> str:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_gate": gate.to_dict(),
        "suites": [result.to_dict() for result in results],
    }
    return json.dumps(payload, indent=2)
