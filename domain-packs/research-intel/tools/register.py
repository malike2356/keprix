"""Register research-intel pack tools (thin wrappers over mesh leads)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.tools.registry import registry

TOOLSET = "domain_pack_research_intel"


def _schema(name: str, description: str, properties: dict, required: list | None = None) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


def _handle_brief_checklist(args: dict[str, Any], **kwargs: Any) -> str:
    topic = str(args.get("topic") or "research brief").strip()
    return json.dumps(
        {
            "topic": topic,
            "checklist": [
                "Define decision question",
                "List trusted sources",
                "Capture evidence with citations",
                "Flag unknowns and confidence",
                "Recommend next action (lead / booking / none)",
            ],
            "pack": "research-intel",
            "glossary_path": str(Path(__file__).resolve().parents[1] / "glossary.json"),
        }
    )


registry.register(
    name="research_intel_brief_checklist",
    toolset=TOOLSET,
    schema=_schema(
        "research_intel_brief_checklist",
        "Return a research brief checklist for Community intel workflows.",
        {"topic": {"type": "string"}},
    ),
    handler=_handle_brief_checklist,
)
