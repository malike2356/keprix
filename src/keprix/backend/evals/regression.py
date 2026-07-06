"""Baseline comparison and regression detection (Prompt 57)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.backend.evals.benchmark import BenchmarkRunResult
from keprix.backend.evals.metrics import aggregate_metrics
from keprix.evals.cost import detect_cost_regression
from keprix.evals.latency import detect_latency_regression


@dataclass
class RegressionComparison:
    passed: bool
    pass_rate_delta: float
    cost_regression: bool
    latency_regression: bool
    regressions: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "pass_rate_delta": self.pass_rate_delta,
            "cost_regression": self.cost_regression,
            "latency_regression": self.latency_regression,
            "regressions": self.regressions,
            "improvements": self.improvements,
        }


def _baseline_path() -> Path:
    root = Path.cwd() / ".keprix" / "evals"
    root.mkdir(parents=True, exist_ok=True)
    return root / "baseline.json"


def save_baseline(results: list[BenchmarkRunResult], *, path: Path | None = None) -> dict[str, Any]:
    metrics = aggregate_metrics(results)
    payload = {
        "pass_rate": metrics.pass_rate,
        "avg_cost_usd": metrics.avg_cost_usd,
        "avg_runtime_ms": metrics.avg_runtime_ms,
        "suites": {
            result.suite: {
                "pass_rate": result.pass_rate,
                "avg_cost_usd": result.avg_cost_usd,
                "avg_runtime_ms": result.avg_runtime_ms,
            }
            for result in results
        },
    }
    target = path or _baseline_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_baseline(*, path: Path | None = None) -> dict[str, Any]:
    target = path or _baseline_path()
    if not target.is_file():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def compare_to_baseline(
    results: list[BenchmarkRunResult],
    baseline: dict[str, Any] | None = None,
    *,
    min_pass_rate_delta: float = -0.05,
    cost_threshold_pct: float = 10.0,
    latency_threshold_pct: float = 15.0,
) -> RegressionComparison:
    baseline = baseline if baseline is not None else load_baseline()
    current = aggregate_metrics(results)
    regressions: list[str] = []
    improvements: list[str] = []

    baseline_pass = float(baseline.get("pass_rate", current.pass_rate))
    pass_delta = current.pass_rate - baseline_pass
    if pass_delta < min_pass_rate_delta:
        regressions.append(
            f"Pass rate dropped {abs(pass_delta):.2%} ({baseline_pass:.2%} -> {current.pass_rate:.2%})"
        )
    elif pass_delta > 0.01:
        improvements.append(f"Pass rate improved {pass_delta:.2%}")

    cost_check = detect_cost_regression(
        current.avg_cost_usd,
        float(baseline.get("avg_cost_usd", 0.0)),
        threshold_pct=cost_threshold_pct,
    )
    latency_check = detect_latency_regression(
        current.avg_runtime_ms,
        float(baseline.get("avg_runtime_ms", 0.0)),
        threshold_pct=latency_threshold_pct,
    )
    if cost_check.detected:
        regressions.append(cost_check.message)
    if latency_check.detected:
        regressions.append(latency_check.message)

    baseline_suites = dict(baseline.get("suites") or {})
    for result in results:
        prev = baseline_suites.get(result.suite)
        if not prev:
            continue
        if result.pass_rate < float(prev.get("pass_rate", result.pass_rate)) - 0.05:
            regressions.append(
                f"Suite {result.suite} pass rate regressed "
                f"({float(prev['pass_rate']):.2%} -> {result.pass_rate:.2%})"
            )

    return RegressionComparison(
        passed=len(regressions) == 0,
        pass_rate_delta=pass_delta,
        cost_regression=cost_check.detected,
        latency_regression=latency_check.detected,
        regressions=regressions,
        improvements=improvements,
    )
