"""Helpers for checking whether a Keprix release can be installed."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

Runner = Callable[[list[str], Path | None], subprocess.CompletedProcess[str]]


def _default_runner(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)


@dataclass
class InstallabilityResult:
    available: bool
    command: list[str]
    detail: str
    recommendation: str


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stderr, result.stdout) if part.strip()).strip()


def unavailable_recommendation(version: str) -> str:
    return (
        f"Keprix {version} is listed in the local changelog, but keprix=={version} "
        "is not available in the configured Python package index yet."
    )


def check_target_installable(
    version: str,
    *,
    runner: Runner = _default_runner,
    cwd: Path | None = None,
) -> InstallabilityResult:
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--dry-run",
        "--no-deps",
        f"keprix=={version}",
    ]
    result = runner(cmd, cwd)
    detail = _combined_output(result)
    if result.returncode == 0:
        return InstallabilityResult(
            available=True,
            command=cmd,
            detail=detail,
            recommendation=f"Keprix {version} is available to install.",
        )
    return InstallabilityResult(
        available=False,
        command=cmd,
        detail=detail,
        recommendation=unavailable_recommendation(version),
    )
