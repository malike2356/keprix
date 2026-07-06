"""Sandbox policy for notebook execution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keprix.research_workspace.notebooks.errors import DangerousCodeError, SandboxError

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

_DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\bos\.system\b", "os.system is blocked; use approved tooling instead"),
    (r"\bsubprocess\b", "subprocess is blocked in sandbox runs"),
    (r"\beval\s*\(", "eval() requires explicit approval"),
    (r"\bexec\s*\(", "exec() requires explicit approval"),
    (r"\b__import__\s*\(", "__import__ requires explicit approval"),
    (r"\bsocket\b", "Network sockets are blocked by default"),
    (r"\burllib\.request\b", "Network access is blocked by default"),
    (r"\brequests\.", "Network access is blocked by default"),
    (r"\bhttpx\.", "Network access is blocked by default"),
]


@dataclass
class SandboxConfig:
    timeout_seconds: int = 60
    allow_network: bool = False
    approve_dangerous: bool = False
    file_allowlist: list[str] = field(default_factory=list)
    memory_limit_mb: int | None = 512


def scan_code(code: str, *, allow_network: bool = False, approve_dangerous: bool = False) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    for pattern, message in _DANGEROUS_PATTERNS:
        if re.search(pattern, code):
            is_network = "Network" in message
            if is_network and allow_network:
                continue
            if not approve_dangerous:
                warnings.append({"pattern": pattern, "message": message})
    return warnings


def assert_code_allowed(code: str, config: SandboxConfig) -> None:
    issues = scan_code(code, allow_network=config.allow_network, approve_dangerous=config.approve_dangerous)
    if issues:
        raise DangerousCodeError("; ".join(item["message"] for item in issues))


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[redacted-secret]", redacted)
    return redacted


def validate_paths(paths: list[Path], *, workdir: Path, allowlist: list[str]) -> None:
    workdir = workdir.resolve()
    allowed = {workdir}
    for item in allowlist:
        allowed.add(Path(item).expanduser().resolve())
    for path in paths:
        resolved = path.expanduser().resolve()
        if not any(resolved == root or root in resolved.parents for root in allowed):
            raise SandboxError(f"Path not in sandbox allowlist: {resolved}")


def repair_suggestions(stderr: str, return_code: int) -> list[str]:
    suggestions: list[str] = []
    text = stderr.lower()
    if return_code != 0 and "modulenotfounderror" in text:
        suggestions.append("Install the missing Python package in the workspace environment or remove the import.")
    if return_code != 0 and "no module named" in text:
        suggestions.append("Check package spelling and whether the optional dependency is installed.")
    if "pandas" in text and "not defined" in text:
        suggestions.append("Add `import pandas as pd` at the top of the cell.")
    if return_code != 0 and "there is no package called" in text:
        suggestions.append("For R, install packages manually with install.packages() after user approval.")
    if return_code != 0 and "syntaxerror" in text:
        suggestions.append("Review Python syntax near the reported line number.")
    if not suggestions and return_code != 0:
        suggestions.append("Inspect execution.log and rerun with approve_dangerous only if required.")
    return suggestions
