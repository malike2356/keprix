"""Registry tool for lawful, bounded OSINT investigations."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from keprix.research.osint.entity import Entity
from keprix.research.osint.orchestrator import investigate
from keprix.research.osint.sources import sources_for
from keprix.research_workspace.store import get_research_workspace_store
from keprix.tools.registry import registry


def _company_registry_source(query: str):
    def fetch(_: Entity) -> list[dict[str, Any]]:
        from keprix.integrations.company_registry import lookup_company

        result = asyncio.run(lookup_company(query))
        rows = []
        for source in result.get("sources") or []:
            rows.append({"claim": f"Registry match for {query}", "url": source, "registration_id": result.get("registration_id")})
        return rows

    return fetch


def osint_investigate(args: dict[str, Any]) -> str:
    if os.environ.get("KEPRIX_OSINT_ENABLED", "").lower() not in {"1", "true", "yes", "on"}:
        return json.dumps({"status": "disabled", "reason": "OSINT is disabled by workspace policy"})
    if not args.get("acknowledge_lawful_use"):
        return json.dumps({"status": "acknowledgement_required", "reason": "lawful-use acknowledgement is required"})
    entity = Entity(str(args.get("kind") or "company"), str(args.get("name") or ""), seed=args.get("seed") or {})
    requested_sources = args.get("sources")
    if requested_sources is not None and not isinstance(requested_sources, list):
        return json.dumps({"status": "invalid_sources", "reason": "sources must be a list"})
    selected_sources = None if requested_sources is None else [name for name in requested_sources if name != "company_registry"]
    try:
        sources = sources_for(entity.kind, selected_sources, limit=int(args.get("limit") or 10))
    except (TypeError, ValueError) as exc:
        return json.dumps({"status": "invalid_sources", "reason": str(exc)})
    if entity.kind == "company" and (requested_sources is None or "company_registry" in requested_sources):
        sources["company_registry"] = _company_registry_source(entity.name)
    result = investigate(
        workspace_id=str(args.get("workspace_id") or "default"),
        entity=entity,
        sources=sources,
        depth_cap=max(1, min(int(args.get("depth_cap") or 2), 5)),
        enabled=True,
        acknowledge_lawful_use=True,
        run_store=get_research_workspace_store(str(args.get("workspace_id") or "default")),
    )
    return json.dumps(result, default=str)


registry.register(
    name="osint_investigate",
    toolset="research",
    schema={
        "name": "osint_investigate",
        "description": "Run a bounded, cited public-record investigation after lawful-use acknowledgement.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "kind": {"type": "string", "enum": ["person", "company", "domain"]},
                "name": {"type": "string"},
                "seed": {"type": "object"},
                "depth_cap": {"type": "integer", "minimum": 1, "maximum": 5},
                "acknowledge_lawful_use": {"type": "boolean"},
                "sources": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["kind", "name", "acknowledge_lawful_use"],
        },
    },
    handler=osint_investigate,
)
