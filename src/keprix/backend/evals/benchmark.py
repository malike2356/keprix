"""Benchmark runner for workflow eval suites (Prompt 57)."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from keprix.backend.evals.datasets import BenchmarkRegistry, BenchmarkTask, benchmark_registry, load_all_benchmarks
from keprix.backend.evals.graders import GraderResult, GradingContext, all_passed, run_graders

TaskExecutor = Callable[[BenchmarkTask], dict[str, Any] | Awaitable[dict[str, Any]]]


@dataclass
class BenchmarkTaskResult:
    task_id: str
    workflow: str
    passed: bool
    reason: str | None = None
    output: str = ""
    blocked: bool = False
    cost_usd: float = 0.0
    runtime_ms: float = 0.0
    safety_warnings: list[str] = field(default_factory=list)
    grader_results: list[GraderResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "workflow": self.workflow,
            "passed": self.passed,
            "reason": self.reason,
            "output": self.output,
            "blocked": self.blocked,
            "cost_usd": self.cost_usd,
            "runtime_ms": self.runtime_ms,
            "safety_warnings": self.safety_warnings,
            "graders": [item.to_dict() for item in self.grader_results],
        }


@dataclass
class BenchmarkRunResult:
    suite: str
    version: str
    workflow: str
    category: str
    passed: int
    total: int
    pass_rate: float
    avg_cost_usd: float
    avg_runtime_ms: float
    safety_warnings: list[str] = field(default_factory=list)
    tasks: list[BenchmarkTaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "version": self.version,
            "workflow": self.workflow,
            "category": self.category,
            "passed": self.passed,
            "total": self.total,
            "pass_rate": self.pass_rate,
            "avg_cost_usd": self.avg_cost_usd,
            "avg_runtime_ms": self.avg_runtime_ms,
            "safety_warnings": self.safety_warnings,
            "tasks": [task.to_dict() for task in self.tasks],
        }


class BenchmarkRunner:
    """Run local benchmark suites without external services by default."""

    def __init__(self, registry: BenchmarkRegistry | None = None) -> None:
        self.registry = registry or benchmark_registry

    async def run_task(
        self,
        task: BenchmarkTask,
        *,
        workflow: str,
        executor: TaskExecutor | None = None,
    ) -> BenchmarkTaskResult:
        started = time.perf_counter()
        safety_warnings: list[str] = []

        if executor is not None:
            payload = executor(task)
            if hasattr(payload, "__await__"):
                payload = await payload
            output = str(payload.get("output", ""))
            blocked = bool(payload.get("blocked", False))
            cost_usd = float(payload.get("cost_usd", 0.0))
            runtime_ms = float(payload.get("runtime_ms", (time.perf_counter() - started) * 1000))
            artifacts = list(payload.get("artifacts") or [])
            tool_calls = list(payload.get("tool_calls") or [])
            safety_violations = list(payload.get("safety_violations") or [])
        else:
            output = str(task.mock_output or "")
            blocked = bool(task.mock_blocked if task.mock_blocked is not None else task.expect_blocked)
            cost_usd = float(task.mock_cost_usd if task.mock_cost_usd is not None else 0.0)
            runtime_ms = float(
                task.mock_latency_ms if task.mock_latency_ms is not None else (time.perf_counter() - started) * 1000
            )
            artifacts = list(task.mock_artifacts)
            tool_calls = list(task.mock_tool_calls)
            safety_violations = []

        if task.max_cost_usd is not None and cost_usd > task.max_cost_usd:
            safety_warnings.append(f"Cost {cost_usd:.4f} exceeds max {task.max_cost_usd:.4f} USD")
        if task.max_runtime_ms is not None and runtime_ms > task.max_runtime_ms:
            safety_warnings.append(f"Runtime {runtime_ms:.1f} ms exceeds max {task.max_runtime_ms:.1f} ms")

        ctx = GradingContext(
            output=output,
            blocked=blocked,
            cost_usd=cost_usd,
            latency_ms=runtime_ms,
            artifacts=artifacts,
            tool_calls=tool_calls,
            safety_violations=safety_violations,
            safety_critical=task.safety_critical,
        )
        grader_results = run_graders(ctx, task.graders)
        passed, reason = all_passed(grader_results)

        if safety_warnings and passed:
            passed = False
            reason = safety_warnings[0]

        return BenchmarkTaskResult(
            task_id=task.id,
            workflow=workflow,
            passed=passed,
            reason=reason,
            output=output,
            blocked=blocked,
            cost_usd=cost_usd,
            runtime_ms=runtime_ms,
            safety_warnings=safety_warnings,
            grader_results=grader_results,
        )

    async def run_suite(
        self,
        suite_name: str,
        *,
        executor: TaskExecutor | None = None,
    ) -> BenchmarkRunResult:
        suite = self.registry.get(suite_name)
        if suite is None:
            raise KeyError(f"Benchmark suite not found: {suite_name}")

        task_results: list[BenchmarkTaskResult] = []
        for task in suite.tasks:
            task_results.append(await self.run_task(task, workflow=suite.workflow, executor=executor))

        passed = sum(1 for result in task_results if result.passed)
        total = len(task_results)
        warnings = [warning for result in task_results for warning in result.safety_warnings]

        return BenchmarkRunResult(
            suite=suite.name,
            version=suite.version,
            workflow=suite.workflow,
            category=suite.category,
            passed=passed,
            total=total,
            pass_rate=passed / total if total else 0.0,
            avg_cost_usd=sum(r.cost_usd for r in task_results) / total if total else 0.0,
            avg_runtime_ms=sum(r.runtime_ms for r in task_results) / total if total else 0.0,
            safety_warnings=warnings,
            tasks=task_results,
        )

    async def run_all(self, *, executor: TaskExecutor | None = None) -> list[BenchmarkRunResult]:
        results: list[BenchmarkRunResult] = []
        for suite_name in self.registry.list_suites():
            results.append(await self.run_suite(suite_name, executor=executor))
        return results

    async def run_workflow(
        self,
        workflow: str,
        *,
        executor: TaskExecutor | None = None,
    ) -> list[BenchmarkRunResult]:
        names = [suite.name for suite in self.registry.list_by_workflow(workflow)]
        results: list[BenchmarkRunResult] = []
        for name in names:
            results.append(await self.run_suite(name, executor=executor))
        return results


def get_benchmark_runner(*, reload: bool = False) -> BenchmarkRunner:
    if reload or not benchmark_registry.list_suites():
        load_all_benchmarks()
    return BenchmarkRunner()
