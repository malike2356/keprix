"""Eval runner and suite execution."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from keprix.evals.datasets import load_all_into_registry
from keprix.evals.registry import EvalRegistry, EvalSuite, EvalTask, eval_registry
from keprix.evals.scorers import score_task

TaskExecutor = Callable[[EvalTask], dict[str, Any] | Awaitable[dict[str, Any]]]


@dataclass
class TaskResult:
    task_id: str
    category: str
    passed: bool
    reason: str | None = None
    output: str = ""
    blocked: bool = False
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    token_usage: int = 0
    tool_failures: int = 0
    retries: int = 0
    trace_id: str | None = None
    expected: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "passed": self.passed,
            "reason": self.reason,
            "output": self.output,
            "blocked": self.blocked,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            "tool_failures": self.tool_failures,
            "retries": self.retries,
            "trace_id": self.trace_id,
            "expected": self.expected,
        }


@dataclass
class SuiteResult:
    suite: str
    version: str
    category: str
    passed: int
    total: int
    pass_rate: float
    avg_cost_usd: float
    avg_latency_ms: float
    tool_failure_rate: float
    retry_rate: float
    tasks: list[TaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "version": self.version,
            "category": self.category,
            "passed": self.passed,
            "total": self.total,
            "pass_rate": self.pass_rate,
            "avg_cost_usd": self.avg_cost_usd,
            "avg_latency_ms": self.avg_latency_ms,
            "tool_failure_rate": self.tool_failure_rate,
            "retry_rate": self.retry_rate,
            "tasks": [task.to_dict() for task in self.tasks],
        }


class EvalRunner:
    """Execute golden task suites with optional live agent executor."""

    def __init__(self, registry: EvalRegistry | None = None) -> None:
        self.registry = registry or eval_registry

    async def run_task(self, task: EvalTask, executor: TaskExecutor | None = None) -> TaskResult:
        started = time.perf_counter()
        if executor is not None:
            payload = executor(task)
            if hasattr(payload, "__await__"):
                payload = await payload
            output = str(payload.get("output", ""))
            blocked = bool(payload.get("blocked", False))
            cost_usd = float(payload.get("cost_usd", 0.0))
            latency_ms = float(payload.get("latency_ms", (time.perf_counter() - started) * 1000))
            token_usage = int(payload.get("token_usage", 0))
            tool_failures = int(payload.get("tool_failures", 0))
            retries = int(payload.get("retries", 0))
        else:
            output = str(task.mock_output or "")
            blocked = bool(task.mock_blocked if task.mock_blocked is not None else task.expect_blocked)
            cost_usd = float(task.mock_cost_usd if task.mock_cost_usd is not None else 0.0)
            latency_ms = float(
                task.mock_latency_ms if task.mock_latency_ms is not None else (time.perf_counter() - started) * 1000
            )
            token_usage = 0
            tool_failures = 0
            retries = 0

        passed, reason = score_task(
            task,
            output=output,
            blocked=blocked,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
        from keprix.evals.trace_store import register_task_trace

        expected = task.expect_contains
        if task.expect_blocked:
            expected = "blocked"
        trace_id = register_task_trace(
            task_id=task.id,
            suite="",
            expected=expected,
            actual=output,
            passed=passed,
            reason=reason,
            category=task.category.value,
        )
        return TaskResult(
            task_id=task.id,
            category=task.category.value,
            passed=passed,
            reason=reason,
            output=output,
            blocked=blocked,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            token_usage=token_usage,
            tool_failures=tool_failures,
            retries=retries,
            trace_id=trace_id,
            expected=expected,
        )

    async def run_suite(
        self,
        suite_name: str,
        *,
        executor: TaskExecutor | None = None,
    ) -> SuiteResult:
        suite = self.registry.get(suite_name)
        if suite is None:
            raise KeyError(f"Eval suite not found: {suite_name}")

        task_results: list[TaskResult] = []
        for task in suite.tasks:
            result = await self.run_task(task, executor=executor)
            if result.trace_id:
                from keprix.evals.trace_store import get_eval_trace_store

                record = get_eval_trace_store().get(result.trace_id)
                if record is not None:
                    record.suite = suite.name
            task_results.append(result)

        passed = sum(1 for result in task_results if result.passed)
        total = len(task_results)
        pass_rate = passed / total if total else 0.0
        avg_cost = sum(result.cost_usd for result in task_results) / total if total else 0.0
        avg_latency = sum(result.latency_ms for result in task_results) / total if total else 0.0
        tool_failures = sum(result.tool_failures for result in task_results)
        retries = sum(result.retries for result in task_results)

        return SuiteResult(
            suite=suite.name,
            version=suite.version,
            category=suite.category.value,
            passed=passed,
            total=total,
            pass_rate=pass_rate,
            avg_cost_usd=avg_cost,
            avg_latency_ms=avg_latency,
            tool_failure_rate=tool_failures / total if total else 0.0,
            retry_rate=retries / total if total else 0.0,
            tasks=task_results,
        )

    async def run_all(self, *, executor: TaskExecutor | None = None) -> list[SuiteResult]:
        results: list[SuiteResult] = []
        for suite_name in self.registry.list_suites():
            results.append(await self.run_suite(suite_name, executor=executor))
        return results


def get_runner(*, reload: bool = False) -> EvalRunner:
    if reload or not eval_registry.list_suites():
        load_all_into_registry()
    return EvalRunner()
