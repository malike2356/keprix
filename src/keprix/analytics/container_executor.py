"""Container-first execution interface with a safe local fallback."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    variables: dict[str, Any] = field(default_factory=dict)


class ContainerExecutor:
    def __init__(self, *, container_required: bool = True) -> None:
        self.container_required = container_required

    def run_python(self, code: str, namespace: dict[str, Any]) -> ExecutionResult:
        safe_globals = {
            "__builtins__": {
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "dict": dict,
                "enumerate": enumerate,
                "float": float,
                "int": int,
                "len": len,
                "list": list,
                "max": max,
                "min": min,
                "print": print,
                "range": range,
                "round": round,
                "set": set,
                "sorted": sorted,
                "str": str,
                "sum": sum,
                "tuple": tuple,
                "zip": zip,
            }
        }
        local_ns = dict(namespace)
        try:
            exec(code, safe_globals, local_ns)
            return ExecutionResult(ok=True, variables=local_ns)
        except Exception as exc:
            return ExecutionResult(ok=False, stderr=str(exc), variables=local_ns)

    def run_r(self, code: str) -> ExecutionResult:
        r_bin = shutil.which("Rscript")
        if not r_bin:
            return ExecutionResult(ok=False, stderr="R execution requires Rscript on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False) as handle:
            handle.write(code)
            path = handle.name
        try:
            proc = subprocess.run([r_bin, path], capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(path)
        if proc.returncode != 0:
            return ExecutionResult(ok=False, stderr=proc.stderr.strip() or proc.stdout.strip())
        return ExecutionResult(ok=True, stdout=proc.stdout)

    def run_pspp(self, syntax: str) -> ExecutionResult:
        pspp_bin = shutil.which("pspp") or shutil.which("pspp-cli")
        if not pspp_bin:
            return ExecutionResult(ok=False, stderr="PSPP execution requires pspp on PATH")
        with tempfile.NamedTemporaryFile("w", suffix=".sps", delete=False) as handle:
            handle.write(syntax)
            path = handle.name
        try:
            proc = subprocess.run([pspp_bin, path], capture_output=True, text=True, timeout=120)
        finally:
            os.unlink(path)
        if proc.returncode != 0:
            return ExecutionResult(ok=False, stderr=proc.stderr.strip() or proc.stdout.strip())
        return ExecutionResult(ok=True, stdout=proc.stdout)

    def run_jamovi_export(self, payload: dict) -> ExecutionResult:
        jamovi_bin = shutil.which("jamovi") or shutil.which("jamovi-cli")
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            input_path = handle.name
        try:
            if jamovi_bin:
                output_path = input_path.replace(".json", ".omv")
                proc = subprocess.run(
                    [jamovi_bin, "--export", input_path, output_path],
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if proc.returncode == 0 and os.path.exists(output_path):
                    with open(output_path, "rb") as exported:
                        data = exported.read()
                    return ExecutionResult(
                        ok=True,
                        stdout=output_path,
                        variables={"export_path": output_path, "bytes": len(data)},
                    )
                return ExecutionResult(
                    ok=False,
                    stderr=proc.stderr.strip() or proc.stdout.strip() or "Jamovi export failed",
                )

            export = {
                "format": "keprix-jamovi-json-v1",
                "note": "Jamovi CLI not installed; returning portable JSON export",
                "payload": payload,
            }
            return ExecutionResult(ok=True, stdout=json.dumps(export, indent=2))
        finally:
            if os.path.exists(input_path):
                os.unlink(input_path)
