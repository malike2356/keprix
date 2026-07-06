"""Safety regression checks."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.evals.registry import EvalCategory, EvalSuite, EvalTask
from keprix.evals.scorers import score_safety


@dataclass
class SafetyCheckResult:
    task_id: str
    passed: bool
    reason: str | None


def is_safety_task(task: EvalTask) -> bool:
    return task.category == EvalCategory.CYBER_SAFETY or task.expect_blocked


def evaluate_safety_task(task: EvalTask, *, blocked: bool) -> SafetyCheckResult:
    passed, reason = score_safety(blocked, task.expect_blocked)
    return SafetyCheckResult(task_id=task.id, passed=passed, reason=reason)


def safety_pass_rate(suite: EvalSuite, blocked_by_task: dict[str, bool]) -> float:
    safety_tasks = [task for task in suite.tasks if is_safety_task(task)]
    if not safety_tasks:
        return 1.0
    passed = sum(
        1
        for task in safety_tasks
        if evaluate_safety_task(task, blocked=blocked_by_task.get(task.id, False)).passed
    )
    return passed / len(safety_tasks)
