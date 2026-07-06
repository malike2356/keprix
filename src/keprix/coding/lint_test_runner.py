"""Lint and test detection, execution, and repair loop."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from keprix.coding.issue_runner import IssueRunRequest, IssueRunResult, run_issue


@dataclass
class CommandResult:
    ok: bool
    command: str
    output: str
    parsed_failures: list[str] = field(default_factory=list)


@dataclass
class RepairLoopResult:
    ok: bool
    attempts: int
    last_test: CommandResult | None = None
    last_lint: CommandResult | None = None
    runs: list[IssueRunResult] = field(default_factory=list)
    error: str | None = None


def detect_test_command(repo_path: Path) -> str | None:
    root = repo_path.resolve()
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() or (root / "tests").is_dir():
        return "python -m pytest -q"
    if (root / "package.json").exists():
        return "npm test --if-present"
    if (root / "Makefile").exists():
        text = (root / "Makefile").read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^test:", text, re.M):
            return "make test"
    if (root / "composer.json").exists():
        return "composer test"
    return None


def detect_lint_command(repo_path: Path) -> str | None:
    root = repo_path.resolve()
    if (root / "pyproject.toml").exists():
        return "python -m ruff check ."
    if (root / "package.json").exists():
        return "npm run lint --if-present"
    return None


def run_command(command: str, repo_path: Path, *, timeout: int = 180) -> CommandResult:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()
        failures = parse_failures(output)
        return CommandResult(ok=proc.returncode == 0, command=command, output=output[:8000], parsed_failures=failures)
    except Exception as exc:
        return CommandResult(ok=False, command=command, output=str(exc), parsed_failures=[str(exc)])


def run_lint(repo_path: Path, command: str | None = None) -> CommandResult:
    cmd = command or detect_lint_command(repo_path)
    if not cmd:
        return CommandResult(ok=True, command="", output="no lint command detected")
    return run_command(cmd, repo_path)


def run_tests(repo_path: Path, command: str | None = None, paths: list[str] | None = None) -> CommandResult:
    cmd = command or detect_test_command(repo_path)
    if not cmd:
        return CommandResult(ok=True, command="", output="no test command detected")
    if paths:
        cmd = f"{cmd} {' '.join(paths)}"
    return run_command(cmd, repo_path)


def parse_failures(output: str) -> list[str]:
    failures: list[str] = []
    patterns = (
        r"FAILED\s+(\S+)",
        r"ERROR\s+(\S+)",
        r"AssertionError:.*",
        r"SyntaxError:.*",
        r"npm ERR!.*",
        r"ruff.*?Found \d+ errors?",
    )
    for pattern in patterns:
        failures.extend(re.findall(pattern, output))
    if not failures and "FAILED" in output:
        failures.append("test failures detected")
    return failures[:20]


def repair_loop(
    repo_path: Path,
    issue: str,
    *,
    test_command: str | None = None,
    lint_command: str | None = None,
    max_attempts: int = 3,
    runner: Callable[[IssueRunRequest], IssueRunResult] = run_issue,
) -> RepairLoopResult:
    runs: list[IssueRunResult] = []
    last_test: CommandResult | None = None
    last_lint: CommandResult | None = None

    for attempt in range(1, max_attempts + 1):
        repair_issue = issue if attempt == 1 else f"{issue}\n\nFix test/lint failures:\n" + "\n".join(
            (last_test.parsed_failures if last_test else []) + (last_lint.parsed_failures if last_lint else [])
        )
        run_result = runner(
            IssueRunRequest(
                issue=repair_issue,
                repo_path=repo_path,
                test_command=None,
                profile="default",
            )
        )
        runs.append(run_result)
        if not run_result.ok:
            return RepairLoopResult(ok=False, attempts=attempt, last_test=last_test, last_lint=last_lint, runs=runs, error=run_result.error)

        last_lint = run_lint(repo_path, lint_command)
        if not last_lint.ok:
            if attempt == max_attempts:
                return RepairLoopResult(ok=False, attempts=attempt, last_test=last_test, last_lint=last_lint, runs=runs, error="lint failed")
            continue

        last_test = run_tests(repo_path, test_command)
        if last_test.ok:
            return RepairLoopResult(ok=True, attempts=attempt, last_test=last_test, last_lint=last_lint, runs=runs)

    return RepairLoopResult(
        ok=False,
        attempts=max_attempts,
        last_test=last_test,
        last_lint=last_lint,
        runs=runs,
        error="max repair attempts reached",
    )
