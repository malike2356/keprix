"""Simple coding benchmark tasks for regression checks."""

from __future__ import annotations

from dataclasses import dataclass

from keprix.coding.issue_runner import IssueRunRequest, IssueRunResult, run_issue


@dataclass
class BenchmarkTask:
    name: str
    issue: str
    test_command: str | None = None
    profile: str = "default"


BUILTIN_TASKS: list[BenchmarkTask] = [
    BenchmarkTask(
        name="append_marker",
        issue="Add marker comment to README.md",
        profile="default",
    ),
    BenchmarkTask(
        name="human_review_gate",
        issue="Add marker to README.md",
        profile="human_review",
    ),
]


@dataclass
class BenchmarkResult:
    task: str
    ok: bool
    run_id: str
    error: str | None = None


def run_benchmark(repo_path: str, tasks: list[BenchmarkTask] | None = None) -> list[BenchmarkResult]:
    selected = tasks or BUILTIN_TASKS
    results: list[BenchmarkResult] = []
    for task in selected:
        result: IssueRunResult = run_issue(
            IssueRunRequest(
                issue=task.issue,
                repo_path=repo_path,
                test_command=task.test_command,
                profile=task.profile,
                dry_run=task.profile == "human_review",
                human_approved=task.profile != "human_review",
            )
        )
        results.append(
            BenchmarkResult(
                task=task.name,
                ok=result.ok or (task.profile == "human_review" and result.error == "human review required"),
                run_id=result.run_id,
                error=result.error,
            )
        )
    return results
