"""Dry-run upgrade: simulate install and run product tests in a sandbox."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .models import DryRunResult
from .copy_filters import upgrade_copy_ignore
from .installability import check_target_installable, unavailable_recommendation

CompletedProcess = subprocess.CompletedProcess[str]
Runner = Callable[[list[str], Path | None], CompletedProcess]


def _default_runner(cmd: list[str], cwd: Path | None = None) -> CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)


def _parse_pytest_counts(stdout: str) -> tuple[int, int, int]:
    total = passed = failed = 0
    match = re.search(r"=+\s+(\d+)\s+passed", stdout)
    if match:
        passed = int(match.group(1))
    fail_match = re.search(r"(\d+)\s+failed", stdout)
    if fail_match:
        failed = int(fail_match.group(1))
    total = passed + failed
    if total == 0:
        collected = re.search(r"collected\s+(\d+)\s+item", stdout)
        if collected:
            total = int(collected.group(1))
    return total, passed, failed


def _extract_failures(stdout: str) -> list[str]:
    lines = stdout.splitlines()
    failures: list[str] = []
    for line in lines:
        if line.startswith("FAILED "):
            failures.append(line.removeprefix("FAILED ").strip())
    return failures[:20]


def _extract_warnings(stdout: str) -> list[str]:
    warnings: list[str] = []
    for line in stdout.splitlines():
        if "DeprecationWarning" in line or "deprecated" in line.lower():
            warnings.append(line.strip())
    return warnings[:20]


@dataclass
class DryRunOptions:
    skip_tests: bool = False
    runner: Runner = _default_runner


def dry_run_upgrade(
    product_name: str,
    target_version: str,
    product_path: Path,
    options: DryRunOptions | None = None,
) -> DryRunResult:
    """Simulate upgrading a product to target_version and run its tests."""
    opts = options or DryRunOptions()
    start = time.time()
    product_path = product_path.expanduser().resolve()

    if opts.skip_tests:
        installability = check_target_installable(target_version, runner=opts.runner, cwd=product_path)
        if not installability.available:
            return DryRunResult(
                product=product_name,
                target_version=target_version,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                warnings=[],
                failed_test_details=[installability.detail],
                duration_seconds=time.time() - start,
                recommendation=installability.recommendation,
            )
        return DryRunResult(
            product=product_name,
            target_version=target_version,
            passed=True,
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            warnings=["Tests skipped via --skip-tests."],
            failed_test_details=[],
            duration_seconds=time.time() - start,
            recommendation="Dry run completed with tests skipped. Review before upgrading.",
        )

    with tempfile.TemporaryDirectory(prefix="keprix_dryrun_") as sandbox_name:
        sandbox = Path(sandbox_name)
        product_copy = sandbox / product_path.name
        shutil.copytree(
            product_path,
            product_copy,
            ignore=upgrade_copy_ignore(product_path),
        )

        venv_path = sandbox / "venv"
        create = opts.runner([shutil.which("python3") or "python3", "-m", "venv", str(venv_path)], None)
        if create.returncode != 0:
            return DryRunResult(
                product=product_name,
                target_version=target_version,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                warnings=[],
                failed_test_details=[f"venv creation failed: {create.stderr}"],
                duration_seconds=time.time() - start,
                recommendation=f"Cannot create sandbox for Keprix {target_version}.",
            )

        pip = venv_path / "bin" / "pip"
        install_keprix = opts.runner([str(pip), "install", f"keprix=={target_version}"], None)
        if install_keprix.returncode != 0:
            detail = (install_keprix.stderr or install_keprix.stdout).strip()
            return DryRunResult(
                product=product_name,
                target_version=target_version,
                passed=False,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                warnings=[],
                failed_test_details=[f"Install failed: {detail}"],
                duration_seconds=time.time() - start,
                recommendation=unavailable_recommendation(target_version),
            )

        tests_dir = product_copy / "tests"
        if not tests_dir.exists():
            return DryRunResult(
                product=product_name,
                target_version=target_version,
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                warnings=["No tests/ directory found; nothing to run."],
                failed_test_details=[],
                duration_seconds=time.time() - start,
                recommendation="No tests found. Consider adding tests before upgrading.",
            )

        pytest_bin = venv_path / "bin" / "pytest"
        test_result = opts.runner(
            [str(pytest_bin), str(tests_dir), "-q", "--tb=short"],
            product_copy,
        )
        total, passed, failed = _parse_pytest_counts(test_result.stdout + test_result.stderr)
        warnings = _extract_warnings(test_result.stdout + test_result.stderr)
        failures = _extract_failures(test_result.stdout + test_result.stderr)
        recommendation = (
            "All tests pass. Safe to upgrade."
            if failed == 0
            else f"{failed} test(s) failed. Fix before upgrading."
        )
        return DryRunResult(
            product=product_name,
            target_version=target_version,
            passed=failed == 0,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            warnings=warnings,
            failed_test_details=failures,
            duration_seconds=time.time() - start,
            recommendation=recommendation,
        )
