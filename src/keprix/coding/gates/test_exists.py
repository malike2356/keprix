"""Test existence preflight gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.coding.preflight_store import PreflightGateResult


def _candidate_tests(repo: Path, changed_file: str) -> list[Path]:
    path = Path(changed_file)
    stem = path.stem
    return [
        repo / "tests" / f"test_{stem}.py",
        repo / "tests" / path.parent / f"test_{stem}.py",
        repo / path.parent / f"test_{stem}.py",
        repo / path.parent / f"{stem}.test.ts",
        repo / path.parent / f"{stem}.test.tsx",
    ]


def run_test_exists_gate(payload: dict[str, Any]) -> PreflightGateResult:
    explicit = payload.get("tests_present")
    if explicit is True:
        return PreflightGateResult("test_exists", "pass", "Relevant tests are already present.", {"explicit": True})
    repo_path = payload.get("repo_path")
    changed_files = [str(item) for item in payload.get("changed_files") or payload.get("target_files") or []]
    if repo_path and changed_files:
        repo = Path(str(repo_path))
        for changed_file in changed_files:
            if any(candidate.is_file() for candidate in _candidate_tests(repo, changed_file)):
                return PreflightGateResult("test_exists", "pass", "A nearby test file exists.", {"file": changed_file})
    return PreflightGateResult("test_exists", "warn", "No nearby test file was found; consider writing the test first.", {"files": changed_files})
