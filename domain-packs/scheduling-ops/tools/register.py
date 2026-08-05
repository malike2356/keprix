"""Register scheduling-ops pack tools (point at viCal mesh)."""

from __future__ import annotations

import json
from typing import Any

from keprix.tools.registry import registry

TOOLSET = "domain_pack_scheduling_ops"


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


def _handle_host_setup(args: dict[str, Any], **kwargs: Any) -> str:
    host = str(args.get("user_id") or args.get("host_user_id") or "default")
    from keprix.vical.seed import ensure_default_consultation

    seeded = ensure_default_consultation(host)
    return json.dumps({"ok": True, "host": host, "seed": seeded, "hub": "/vical"})


registry.register(
    name="scheduling_ops_ensure_host",
    toolset=TOOLSET,
    schema=_schema(
        "scheduling_ops_ensure_host",
        "Ensure default Consultation event type and host profile for viCal.",
        {"user_id": {"type": "string"}},
    ),
    handler=_handle_host_setup,
)
