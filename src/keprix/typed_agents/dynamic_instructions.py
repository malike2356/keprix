"""Dynamic instruction builders for typed agents."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from keprix.typed_agents.schemas import AgentRunContext

InstructionFn = Callable[[Any, AgentRunContext], str]


def build_instructions(
    base_instructions: str,
    deps: Any,
    context: AgentRunContext,
    *,
    dynamic: list[InstructionFn] | None = None,
) -> str:
    sections = [base_instructions.strip()]
    if hasattr(deps, "prompt_safe_dict"):
        safe = deps.prompt_safe_dict()
        sections.append("Runtime context:\n" + _format_context(safe))
    else:
        sections.append("Runtime context:\n" + _format_context(_safe_fallback(deps)))
    for builder in dynamic or []:
        extra = builder(deps, context).strip()
        if extra:
            sections.append(extra)
    sections.append(f"Trace ID: {context.trace_id}")
    sections.append(f"Prompt version: {context.prompt_version}")
    return "\n\n".join(section for section in sections if section)


def _format_context(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, dict):
            lines.append(f"- {key}: {_compact_dict(value)}")
        elif isinstance(value, list):
            lines.append(f"- {key}: {', '.join(str(item) for item in value)}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _compact_dict(value: dict[str, Any]) -> str:
    return ", ".join(f"{key}={item}" for key, item in value.items())


def _safe_fallback(deps: Any) -> dict[str, Any]:
    if isinstance(deps, dict):
        return {key: value for key, value in deps.items() if "secret" not in key.lower()}
    return {"type": deps.__class__.__name__}
