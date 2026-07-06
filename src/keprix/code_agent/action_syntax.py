"""Parse and validate code-first agent action snippets."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_BANNED_IMPORTS = {
    "subprocess",
    "socket",
    "ctypes",
    "pty",
    "fcntl",
    "resource",
    "multiprocessing",
}
_BANNED_CALLS = {"eval", "exec", "compile", "__import__", "open"}


@dataclass
class ActionParseResult:
    ok: bool
    code: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class CodePolicy:
    allowed_imports: set[str] = field(default_factory=lambda: {"json", "math", "statistics", "datetime", "collections"})
    allowed_paths: set[str] = field(default_factory=set)
    allow_network: bool = False
    max_runtime_s: int = 30
    memory_limit_mb: int = 256
    approval_threshold: str = "medium"
    output_schema: dict | None = None


def extract_code(text: str) -> ActionParseResult:
    match = _CODE_BLOCK_RE.search(text)
    code = match.group(1).strip() if match else text.strip()
    if not code:
        return ActionParseResult(ok=False, errors=["no code found"])
    return ActionParseResult(ok=True, code=code)


def validate_code(code: str, policy: CodePolicy) -> ActionParseResult:
    errors: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return ActionParseResult(ok=False, code=code, errors=[f"syntax error: {exc}"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BANNED_IMPORTS or root not in policy.allowed_imports:
                    errors.append(f"import blocked: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module in _BANNED_IMPORTS or (module and module not in policy.allowed_imports):
                errors.append(f"import blocked: {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in _BANNED_CALLS:
                errors.append(f"call blocked: {node.func.id}")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "os" and node.attr in {"system", "popen", "remove", "unlink"}:
                errors.append(f"os access blocked: os.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "/etc/" in node.value or ".." in node.value:
                if policy.allowed_paths and not any(node.value.startswith(path) for path in policy.allowed_paths):
                    errors.append(f"path blocked: {node.value}")

    if errors:
        return ActionParseResult(ok=False, code=code, errors=errors)
    return ActionParseResult(ok=True, code=code)
