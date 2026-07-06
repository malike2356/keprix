"""Namespace isolation checks for generated tools."""

from __future__ import annotations

_GENERATED_TOOL_NAMESPACE = "keprix.generated_tools"
_FORBIDDEN_INTERNAL_PREFIXES = (
    "keprix.",
    "keprix_sdk.",
    "backend.auth",
    "backend.security",
    "backend.vault",
    "agent.keprix",
)


def validate_tool_imports(tool_code: str) -> list[str]:
    """Reject tools that try to import keprix internals."""
    violations: list[str] = []
    for prefix in _FORBIDDEN_INTERNAL_PREFIXES:
        if prefix in tool_code:
            violations.append(f"Generated tool attempts to import internal module: {prefix}")
    return violations
