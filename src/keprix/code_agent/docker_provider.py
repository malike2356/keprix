"""Docker sandbox provider for code agent execution."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path

from keprix.code_agent.action_syntax import CodePolicy
from keprix.code_agent.sandbox_provider import SandboxProvider, SandboxSession, SandboxResult

_RUNNER = textwrap.dedent(
    """
    import json
    import runpy
    import sys
    from pathlib import Path

    code_path = Path(sys.argv[1])
    namespace = {"__name__": "__main__"}
    exec(code_path.read_text(encoding="utf-8"), namespace, namespace)
    if "result" in namespace:
        print(json.dumps({"result": namespace["result"]}))
    """
).strip()


class DockerSandboxProvider(SandboxProvider):
    name = "docker"

    def __init__(self, policy: CodePolicy | None = None) -> None:
        self.policy = policy or CodePolicy()
        self._sessions: dict[str, SandboxSession] = {}

    def start(self, workspace_id: str) -> SandboxSession:
        session = SandboxSession(
            session_id=self.create_session_id(),
            workspace_id=workspace_id,
            provider=self.name,
            metadata={"memory_limit_mb": self.policy.memory_limit_mb},
        )
        self._sessions[session.session_id] = session
        return session

    def run_code(self, session_id: str, code: str) -> SandboxResult:
        session = self._sessions.get(session_id)
        if session is None:
            return SandboxResult(ok=False, error="unknown session")
        if shutil.which("docker"):
            result = self._run_docker(code)
            if not result.ok:
                return self._run_local(code)
            return result
        return self._run_local(code)

    def stop(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _run_docker(self, code: str) -> SandboxResult:
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="keprix_code_agent_") as tmp:
            sandbox = Path(tmp)
            code_path = sandbox / "agent_code.py"
            runner_path = sandbox / "runner.py"
            code_path.write_text(code, encoding="utf-8")
            runner_path.write_text(_RUNNER, encoding="utf-8")
            cmd = [
                "docker",
                "run",
                "--rm",
                "--network=none",
                f"--memory={self.policy.memory_limit_mb}m",
                f"--memory-swap={self.policy.memory_limit_mb}m",
                "--cpus=0.5",
                "-v",
                f"{sandbox}:/sandbox:ro",
                "python:3.11-slim",
                "python",
                "/sandbox/runner.py",
                "/sandbox/agent_code.py",
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.policy.max_runtime_s,
                )
            except subprocess.TimeoutExpired:
                return SandboxResult(ok=False, error="execution timed out", duration_ms=int((time.perf_counter() - started) * 1000))
            duration_ms = int((time.perf_counter() - started) * 1000)
            data: dict = {}
            stdout = proc.stdout or ""
            if stdout.strip():
                try:
                    data = json.loads(stdout.strip().splitlines()[-1])
                except json.JSONDecodeError:
                    data = {"raw": stdout.strip()}
            return SandboxResult(
                ok=proc.returncode == 0,
                stdout=stdout,
                stderr=proc.stderr or "",
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                data=data,
                error=None if proc.returncode == 0 else "docker execution failed",
            )

    def _run_local(self, code: str) -> SandboxResult:
        started = time.perf_counter()
        namespace: dict = {}
        try:
            exec(code, namespace, namespace)
            result = namespace.get("result")
            duration_ms = int((time.perf_counter() - started) * 1000)
            payload = json.dumps({"result": result}) if result is not None else ""
            return SandboxResult(ok=True, stdout=payload, duration_ms=duration_ms, data={"result": result})
        except Exception as exc:
            return SandboxResult(ok=False, stderr=str(exc), error=str(exc), duration_ms=int((time.perf_counter() - started) * 1000))
