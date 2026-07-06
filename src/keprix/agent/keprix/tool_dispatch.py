"""Keprix tool dispatch result types and registry wrapper (Prompt 143)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

ToolDispatchErrorCode = Literal["ok", "not_found", "blocked", "failed", "quarantined"]


@dataclass(frozen=True)
class ToolDispatchResult:
    ok: bool
    error_code: ToolDispatchErrorCode
    tool_name: str | None
    message: str
    result: str | None = None


def classify_registry_result(tool_name: str, raw: str) -> ToolDispatchResult:
    """Classify a registry JSON string into a structured dispatch result."""
    lowered = (raw or "").lower()
    if "unknown tool" in lowered:
        return ToolDispatchResult(
            ok=False,
            error_code="not_found",
            tool_name=tool_name,
            message=f"Unknown tool: {tool_name}",
            result=raw,
        )
    if "quarantined" in lowered:
        return ToolDispatchResult(
            ok=False,
            error_code="quarantined",
            tool_name=tool_name,
            message=raw,
            result=raw,
        )
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return ToolDispatchResult(
            ok=True,
            error_code="ok",
            tool_name=tool_name,
            message="ok",
            result=raw,
        )
    if isinstance(payload, dict) and payload.get("error"):
        error_text = str(payload.get("error") or "")
        if "unknown tool" in error_text.lower():
            code: ToolDispatchErrorCode = "not_found"
        elif "quarantined" in error_text.lower():
            code = "quarantined"
        elif "block" in error_text.lower():
            code = "blocked"
        else:
            code = "failed"
        return ToolDispatchResult(
            ok=False,
            error_code=code,
            tool_name=tool_name,
            message=error_text,
            result=raw,
        )
    return ToolDispatchResult(
        ok=True,
        error_code="ok",
        tool_name=tool_name,
        message="ok",
        result=raw,
    )


def dispatch_tool(tool_name: str, args: dict[str, Any] | None = None, **kwargs: Any) -> ToolDispatchResult:
    from tools.registry import registry

    raw = registry.dispatch(tool_name, dict(args or {}), **kwargs)
    return classify_registry_result(tool_name, raw)


def is_tool_registered(tool_name: str) -> bool:
    from tools.registry import registry

    return registry.get_entry(tool_name) is not None
