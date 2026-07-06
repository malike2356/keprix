"""Subprocess sandbox for synthesized tool validation (Prompt 150)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxResult:
    passed: bool
    error: str | None
    stderr: str
    stdout: str
    duration_ms: int
    schema_valid: bool
    detected_function_name: str | None


def validate_tool_in_sandbox(
    source_code: str,
    tool_name: str,
    timeout_seconds: int = 10,
    memory_limit_mb: int = 128,
) -> SandboxResult:
    """Run tool source in an isolated subprocess. Never raises."""
    _ = memory_limit_mb
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="keprix_mutation_sandbox_") as tmp:
        tool_path = Path(tmp) / "generated_tool.py"
        runner_path = Path(tmp) / "run_sandbox.py"
        tool_path.write_text(source_code, encoding="utf-8")
        runner_path.write_text(_build_sandbox_harness(), encoding="utf-8")
        env = {
            "PYTHONPATH": "",
            "KEPRIX_SANDBOX": "true",
            "PATH": "/usr/bin:/bin",
        }
        try:
            proc = subprocess.run(
                [sys.executable, str(runner_path), str(tool_path), tool_name],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=tmp,
                env=env,
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return SandboxResult(
                passed=False,
                error="sandbox timeout",
                stderr="",
                stdout="",
                duration_ms=duration_ms,
                schema_valid=False,
                detected_function_name=None,
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return SandboxResult(
                passed=False,
                error=str(exc),
                stderr="",
                stdout="",
                duration_ms=duration_ms,
                schema_valid=False,
                detected_function_name=None,
            )

    duration_ms = int((time.perf_counter() - started) * 1000)
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    if proc.returncode != 0:
        return SandboxResult(
            passed=False,
            error=stderr or stdout or f"exit {proc.returncode}",
            stderr=stderr,
            stdout=stdout,
            duration_ms=duration_ms,
            schema_valid=False,
            detected_function_name=None,
        )
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        return SandboxResult(
            passed=False,
            error="sandbox harness returned invalid JSON",
            stderr=stderr,
            stdout=stdout,
            duration_ms=duration_ms,
            schema_valid=False,
            detected_function_name=None,
        )
    return SandboxResult(
        passed=bool(payload.get("passed")),
        error=payload.get("error"),
        stderr=stderr,
        stdout=stdout,
        duration_ms=duration_ms,
        schema_valid=bool(payload.get("schema_valid")),
        detected_function_name=payload.get("detected_function_name"),
    )


def _build_sandbox_harness() -> str:
    return textwrap.dedent(
        '''
        import importlib.util
        import json
        import sys
        import types

        class _MockRegistry:
            def __init__(self):
                self.calls = []

            def register(self, name, toolset="generated", schema=None, handler=None, **kwargs):
                description = kwargs.get("description") or ""
                if schema is None and kwargs.get("input_schema") is not None:
                    schema = {
                        "name": name,
                        "description": description or name,
                        "parameters": kwargs.get("input_schema"),
                    }
                self.calls.append(
                    {
                        "name": name,
                        "toolset": toolset,
                        "schema": schema or {},
                        "handler": handler,
                        "description": description or (schema or {}).get("description", ""),
                    }
                )

        registry = _MockRegistry()
        tools_pkg = types.ModuleType("tools")
        registry_mod = types.ModuleType("tools.registry")
        registry_mod.registry = registry
        registry_mod.tool_error = lambda message, **extra: json.dumps({"error": str(message), **extra})
        registry_mod.tool_result = lambda data=None, **kwargs: json.dumps(data if data is not None else kwargs)
        sys.modules["tools"] = tools_pkg
        sys.modules["tools.registry"] = registry_mod
        tools_pkg.registry = registry_mod

        def main():
            tool_path, tool_name = sys.argv[1], sys.argv[2]
            spec = importlib.util.spec_from_file_location("generated_tool", tool_path)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                print(json.dumps({"passed": False, "error": f"import failed: {exc}"}))
                return

            if len(registry.calls) != 1:
                print(json.dumps({"passed": False, "error": "registry.register must be called exactly once"}))
                return

            call = registry.calls[0]
            schema = call.get("schema") or {}
            description = call.get("description") or schema.get("description") or ""
            if not call.get("name") or not description:
                print(json.dumps({"passed": False, "error": "registered schema missing name or description"}))
                return

            handler = call.get("handler")
            if handler is None or not callable(handler):
                print(json.dumps({"passed": False, "error": "registered handler is not callable"}))
                return

            detected = getattr(handler, "__name__", None)
            try:
                if handler.__code__.co_argcount >= 1 and handler.__code__.co_varnames[0] == "input_str":
                    handler("")
                    handler("{}")
                else:
                    handler({})
                    handler({"query": "sandbox"})
            except Exception as exc:
                print(json.dumps({"passed": False, "error": f"handler call failed: {exc}", "detected_function_name": detected}))
                return

            print(
                json.dumps(
                    {
                        "passed": True,
                        "error": None,
                        "schema_valid": True,
                        "detected_function_name": detected,
                    }
                )
            )

        if __name__ == "__main__":
            main()
        '''
    ).strip() + "\n"
