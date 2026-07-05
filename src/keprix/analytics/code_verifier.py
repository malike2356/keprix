"""Safety verifier for generated analytics code."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


ALLOWED_IMPORTS = {
    "collections",
    "csv",
    "datetime",
    "itertools",
    "json",
    "math",
    "numpy",
    "pandas",
    "statistics",
}

BLOCKED_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
    "input",
}

BLOCKED_MODULES = {
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "requests",
    "httpx",
}


@dataclass(slots=True)
class VerificationResult:
    allowed: bool
    errors: list[str] = field(default_factory=list)
    estimated_runtime_seconds: int = 5
    estimated_memory_mb: int = 256


class CodeVerifier:
    def verify(self, code: str, *, network_approved: bool = False, shell_approved: bool = False) -> VerificationResult:
        errors: list[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return VerificationResult(False, [f"Syntax error: {exc.msg}"])

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                errors.extend(self._check_import(node, network_approved=network_approved))
            if isinstance(node, ast.Call):
                errors.extend(self._check_call(node, shell_approved=shell_approved))
            if isinstance(node, ast.Attribute) and node.attr in {"system", "popen", "remove", "unlink"}:
                errors.append(f"Blocked attribute access: {node.attr}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "../" in node.value or node.value.startswith("/"):
                    errors.append("Filesystem escape path blocked")

        return VerificationResult(allowed=not errors, errors=errors)

    def _check_import(self, node: ast.Import | ast.ImportFrom, *, network_approved: bool) -> list[str]:
        errors: list[str] = []
        names = [alias.name.split(".")[0] for alias in getattr(node, "names", [])]
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module.split(".")[0])
        for name in names:
            if name in {"requests", "httpx"} and network_approved:
                continue
            if name in BLOCKED_MODULES or name not in ALLOWED_IMPORTS:
                errors.append(f"Import not allowed: {name}")
        return errors

    def _check_call(self, node: ast.Call, *, shell_approved: bool) -> list[str]:
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name in BLOCKED_CALLS:
            return [f"Call blocked: {name}"]
        if name in {"system", "popen", "run", "call"} and not shell_approved:
            return [f"Shell call blocked: {name}"]
        return []
