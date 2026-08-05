"""Workflow variable helpers for Studio playbooks."""

from __future__ import annotations

import re
from typing import Any

STATE_REF_RE = re.compile(r"{{\s*state\.([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def build_initial_state(
    variables: list[dict[str, Any]],
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge variable defaults with run overrides into the playbook state namespace."""
    state: dict[str, Any] = {}
    overrides = overrides or {}
    for variable in variables:
        name = str(variable.get("name") or "")
        if not name:
            continue
        value = overrides[name] if name in overrides else variable.get("default")
        state[name] = _coerce_value(value, str(variable.get("type") or "string"))
    return state


def validate_variable_refs(yaml_doc: dict[str, Any]) -> list[str]:
    """Warn for ``{{ state.name }}`` refs where ``name`` is not declared."""
    declared = {str(item.get("name")) for item in list(yaml_doc.get("variables") or []) if item.get("name")}
    text = str(yaml_doc)
    warnings: list[str] = []
    for name in sorted(set(STATE_REF_RE.findall(text))):
        if name not in declared:
            warnings.append(f"state.{name} is referenced but not declared in variables")
    return warnings


def _coerce_value(value: Any, variable_type: str) -> Any:
    if variable_type == "number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
    if variable_type == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}
    return "" if value is None else str(value)
