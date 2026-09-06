"""Agent tool for optional global company registry lookups."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tools.registry import registry


def company_registry_lookup(args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        return json.dumps({"error": "query is required"})
    try:
        from keprix.integrations.company_registry import lookup_company

        return json.dumps(
            asyncio.run(lookup_company(query, jurisdiction=args.get("jurisdiction"))), default=str
        )
    except Exception as exc:
        return json.dumps({"error": str(exc)})


registry.register(
    name="company_registry_lookup",
    toolset="crm",
    schema={
        "name": "company_registry_lookup",
        "description": (
            "Look up a non-UK company in optional OpenCorporates, GLEIF, and SEC EDGAR registries."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "jurisdiction": {"type": "string"}},
            "required": ["query"],
        },
    },
    handler=company_registry_lookup,
)
