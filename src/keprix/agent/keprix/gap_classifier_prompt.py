"""Prompt templates for LLM-based mutation gap classification."""

from __future__ import annotations

_MAX_MANIFEST_TOOLS = 40

_SYSTEM_PROMPT = """You classify whether a user task requires a tool that is not available.

Respond with JSON only. No markdown fences or commentary.

Schema:
{
  "has_gap": boolean,
  "gap_description": "string",
  "candidate_tool_name": "snake_case",
  "candidate_approach": "string",
  "confidence": 0.0
}

Rules:
- has_gap is true only when no listed tool can reasonably complete the task.
- candidate_tool_name must be snake_case, short, and describe the missing capability.
- confidence is between 0.0 and 1.0.
- General knowledge questions, greetings, and chit-chat have has_gap false.
- If an existing tool already covers the task, set has_gap false even if wording differs.
"""


def _tool_description(name: str) -> str:
    try:
        from tools.registry import registry

        entry = registry.get_entry(name)
        if entry and entry.schema:
            description = str(entry.schema.get("description") or "").strip()
            if description:
                return description[:200]
    except Exception:
        return name
    return name


def build_tool_manifest(available_tools: list[str]) -> str:
    names = list(available_tools)
    lines: list[str] = []
    for name in names[:_MAX_MANIFEST_TOOLS]:
        lines.append(f"- {name}: {_tool_description(name)}")
    if len(names) > _MAX_MANIFEST_TOOLS:
        lines.append(f"... and {len(names) - _MAX_MANIFEST_TOOLS} more")
    return "\n".join(lines) if lines else "(no tools registered)"


def build_gap_classifier_messages(task: str, available_tools: list[str]) -> list[dict[str, str]]:
    manifest = build_tool_manifest(available_tools)
    user_content = (
        "User task (verbatim):\n"
        f"{task.strip()}\n\n"
        "Available tools:\n"
        f"{manifest}\n\n"
        "Return JSON only."
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def parse_gap_classifier_response(raw: str, *, task: str) -> dict:
    """Parse classifier JSON; returns a dict safe for GapReport construction."""
    from keprix.agent.keprix.synthesiser import _extract_json_payload

    payload = _extract_json_payload(raw)
    if not payload:
        return {"has_gap": False, "confidence": 0.0, "task": task}

    has_gap = bool(payload.get("has_gap"))
    confidence = float(payload.get("confidence") or 0.0)
    return {
        "has_gap": has_gap,
        "gap_description": str(payload.get("gap_description") or "").strip(),
        "candidate_tool_name": str(payload.get("candidate_tool_name") or "").strip(),
        "candidate_approach": str(payload.get("candidate_approach") or "").strip(),
        "confidence": max(0.0, min(1.0, confidence)),
        "task": task,
    }
