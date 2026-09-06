"""Agent-facing scoped workspace export tool."""

from __future__ import annotations

import json

from tools.registry import registry

from keprix.document_vault.channel.scoped_export import export_scoped


def workspace_export(args: dict) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return json.dumps({"error": "workspace_id is required"})
    result = export_scoped(workspace_id, str(args.get("kinds") or "all"), "local")
    result.pop("bytes", None)
    return json.dumps(result)


registry.register(
    name="workspace_export",
    toolset="workspace",
    schema={
        "name": "workspace_export",
        "description": "Build a scoped workspace export with a manifest and return its local export metadata.",
        "parameters": {
            "type": "object",
            "properties": {"workspace_id": {"type": "string"}, "kinds": {"type": "string"}},
            "required": ["workspace_id"],
        },
    },
    handler=workspace_export,
    check_fn=lambda: True,
)
