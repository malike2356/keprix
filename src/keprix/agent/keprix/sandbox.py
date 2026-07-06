"""Sandbox runner for generated tools."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

from keprix.agent.keprix.config import get_mutation_config
from keprix.agent.keprix.schemas import SandboxResult

SECCOMP_PROFILE = Path(__file__).resolve().parent / "sandbox" / "seccomp-tool.json"

_TOOL_RUNNER = textwrap.dedent(
    """
    import importlib.util
    import json
    import sys
    from pathlib import Path

    tool_path = Path(sys.argv[1])
    payload = json.loads(sys.argv[2])
    spec = importlib.util.spec_from_file_location("generated_tool", tool_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from tools.registry import registry

    name = payload.get("tool_name")
    entry = registry.get_entry(name)
    if entry is None:
        print(json.dumps({"error": "tool not registered"}))
        sys.exit(2)
    result = entry.handler(payload.get("args") or {}, store=None)
    print(json.dumps({"result": result}))
    """
).strip()


class SandboxRunner:
    async def run(self, tool_code: str, test_input: dict, tool_name: str, timeout_s: int | None = None) -> SandboxResult:
        config = get_mutation_config()
        timeout = timeout_s or config.sandbox_timeout_s
        if shutil.which("docker"):
            docker_result = await self._run_docker(tool_code, test_input, tool_name, timeout)
            if docker_result is not None:
                return docker_result
        return await self._run_local(tool_code, test_input, tool_name, timeout)

    async def _run_docker(
        self,
        tool_code: str,
        test_input: dict,
        tool_name: str,
        timeout: int,
    ) -> SandboxResult | None:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="keprix_sandbox_") as tmp:
            sandbox = Path(tmp)
            tool_path = sandbox / "generated_tool.py"
            runner_path = sandbox / "tool_runner.py"
            tool_path.write_text(tool_code, encoding="utf-8")
            runner_path.write_text(_TOOL_RUNNER, encoding="utf-8")
            payload = json.dumps({"tool_name": tool_name, "args": test_input})
            cmd = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                "--memory=256m",
                "--memory-swap=256m",
                "--cpus=0.5",
                "--read-only",
                "--tmpfs",
                "/tmp:size=32m,noexec",
                "--cap-drop=ALL",
                "--no-new-privileges",
                "-v",
                f"{sandbox}:/sandbox:ro",
            ]
            if SECCOMP_PROFILE.exists():
                cmd.extend([f"--security-opt=seccomp={SECCOMP_PROFILE}"])
            cmd.extend(
                [
                    "python:3.11-slim",
                    "python",
                    "/sandbox/tool_runner.py",
                    "/sandbox/generated_tool.py",
                    payload,
                ]
            )
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return None
            duration_ms = int((time.perf_counter() - started) * 1000)
            stderr = proc.stderr.strip()
            if proc.returncode == 125 or "unknown flag" in stderr.lower():
                return None
            passed = proc.returncode == 0 and "result" in proc.stdout
            return SandboxResult(
                passed=passed,
                output=proc.stdout.strip(),
                stderr=stderr,
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                memory_mb=0.0,
                mode="docker",
            )

    async def _run_local(self, tool_code: str, test_input: dict, tool_name: str, timeout: int) -> SandboxResult:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="keprix_sandbox_local_") as tmp:
            sandbox = Path(tmp)
            tool_path = sandbox / "generated_tool.py"
            runner_path = sandbox / "tool_runner.py"
            tool_path.write_text(tool_code, encoding="utf-8")
            runner_path.write_text(_TOOL_RUNNER, encoding="utf-8")
            payload = json.dumps({"tool_name": tool_name, "args": test_input})
            env = {"PYTHONPATH": str(Path(__file__).resolve().parents[3])}
            try:
                proc = subprocess.run(
                    ["python3", str(runner_path), str(tool_path), payload],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                return SandboxResult(passed=False, output="", stderr="timeout", exit_code=124, duration_ms=timeout * 1000, mode="local")
            duration_ms = int((time.perf_counter() - started) * 1000)
            passed = proc.returncode == 0 and "result" in proc.stdout
            return SandboxResult(
                passed=passed,
                output=proc.stdout.strip(),
                stderr=proc.stderr.strip(),
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                memory_mb=12.0,
                mode="local",
            )
