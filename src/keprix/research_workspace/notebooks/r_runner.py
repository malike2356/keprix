"""R script runner."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.research_workspace.notebooks.errors import NotebookRunError, RunnerNotInstalledError
from keprix.research_workspace.notebooks.kernel_manager import detect_r
from keprix.research_workspace.notebooks.sandbox import SandboxConfig, assert_code_allowed, redact_secrets, repair_suggestions


@dataclass
class ExecutionResult:
    return_code: int
    stdout: str
    stderr: str
    log_path: str
    artifacts: dict[str, Any]
    repair_suggestions: list[str]


def run_r_script(
    *,
    workdir: Path,
    script_path: Path,
    config: SandboxConfig,
    dataset_path: Path | None = None,
) -> ExecutionResult:
    detection = detect_r()
    if not detection.installed:
        raise RunnerNotInstalledError(detection.setup_instructions)
    binary = detection.binary
    assert binary is not None
    code = script_path.read_text(encoding="utf-8")
    assert_code_allowed(code, config)
    try:
        completed = subprocess.run(
            [binary, str(script_path.name)],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise NotebookRunError(f"R runtime exceeded {config.timeout_seconds}s") from exc
    log_path = workdir / "execution.log"
    stdout = redact_secrets(completed.stdout or "")
    stderr = redact_secrets(completed.stderr or "")
    log_path.write_text(
        json.dumps(
            {
                "runtime": "r",
                "return_code": completed.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "dataset_path": str(dataset_path) if dataset_path else None,
                "optional_packages": detection.optional_packages,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    figures = sorted(str(path) for path in workdir.glob("*.png"))
    tables = sorted(str(path) for path in workdir.glob("*.csv"))
    return ExecutionResult(
        return_code=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        log_path=str(log_path),
        artifacts={"figures": figures, "tables": tables},
        repair_suggestions=repair_suggestions(stderr, completed.returncode),
    )
