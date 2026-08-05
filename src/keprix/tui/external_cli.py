"""External CLI launcher for TUI integrations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CliResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run_cli(command: list[str], *, timeout: float = 30.0) -> CliResult:
    proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    return CliResult(command=tuple(command), returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)

