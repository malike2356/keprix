"""Benchmark reports with trend history and failure summaries (Prompt 57)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from keprix.backend.evals.benchmark import BenchmarkRunResult
from keprix.backend.evals.metrics import EvalMetrics, aggregate_metrics


@dataclass
class BenchmarkReport:
    generated_at: str
    passed: bool
    pass_rate: float
    metrics: EvalMetrics
    failures: list[str] = field(default_factory=list)
    safety_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "metrics": self.metrics.to_dict(),
            "failures": self.failures,
            "safety_warnings": self.safety_warnings,
        }


def build_report(
    results: list[BenchmarkRunResult],
    *,
    min_pass_rate: float = 0.9,
) -> BenchmarkReport:
    metrics = aggregate_metrics(results)
    failures: list[str] = []
    warnings: list[str] = []
    for result in results:
        warnings.extend(result.safety_warnings)
        for task in result.tasks:
            if not task.passed and task.reason:
                failures.append(f"{result.suite}/{task.task_id}: {task.reason}")
        if result.pass_rate < min_pass_rate:
            failures.append(f"Suite {result.suite} pass rate {result.pass_rate:.2%} below {min_pass_rate:.2%}")

    passed = metrics.pass_rate >= min_pass_rate and not failures
    return BenchmarkReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        passed=passed,
        pass_rate=metrics.pass_rate,
        metrics=metrics,
        failures=failures,
        safety_warnings=warnings,
    )


def render_markdown_report(report: BenchmarkReport, results: list[BenchmarkRunResult]) -> str:
    lines = [
        "# Keprix Benchmark Report",
        "",
        f"Generated: {report.generated_at}",
        "",
        f"Overall: {'PASS' if report.passed else 'FAIL'}",
        f"Pass rate: {report.pass_rate:.2%}",
        f"Avg cost: ${report.metrics.avg_cost_usd:.4f}",
        f"Avg runtime: {report.metrics.avg_runtime_ms:.1f} ms",
        "",
        "## Suites",
        "",
    ]
    for result in results:
        lines.append(f"### {result.suite} ({result.workflow})")
        lines.append(f"- Pass rate: {result.pass_rate:.2%} ({result.passed}/{result.total})")
        lines.append(f"- Avg cost: ${result.avg_cost_usd:.4f}")
        lines.append(f"- Avg runtime: {result.avg_runtime_ms:.1f} ms")
        for task in result.tasks:
            status = "PASS" if task.passed else "FAIL"
            lines.append(f"  - {status} `{task.task_id}`")
            if task.reason:
                lines.append(f"    - {task.reason}")
        lines.append("")

    if report.safety_warnings:
        lines.append("## Safety warnings")
        lines.extend(f"- {item}" for item in report.safety_warnings)
        lines.append("")

    if report.failures:
        lines.append("## Failures")
        lines.extend(f"- {item}" for item in report.failures)

    return "\n".join(lines)


def render_json_report(report: BenchmarkReport, results: list[BenchmarkRunResult]) -> str:
    payload = {
        "report": report.to_dict(),
        "suites": [result.to_dict() for result in results],
    }
    return json.dumps(payload, indent=2)


def failure_summary(report: BenchmarkReport) -> dict[str, Any]:
    return {
        "failure_count": report.metrics.failure_count,
        "failures": report.failures,
        "safety_warnings": report.safety_warnings,
    }
