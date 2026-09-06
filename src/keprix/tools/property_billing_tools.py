"""Agent-facing property entitlement status tools."""

from __future__ import annotations

import json

from keprix.property_data.billing import workspace_property_entitlement
from keprix.tools.registry import registry


def property_entitlement_limits(args: dict) -> str:
    return json.dumps(workspace_property_entitlement(str(args.get("workspace_id") or "default")))


def property_domain_pack_get(args: dict) -> str:
    from pathlib import Path
    import yaml
    path = Path(__file__).parents[1] / "discovery" / "packs" / "property.yaml"
    return json.dumps(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


registry.register(name="property_entitlement_limits", toolset="property", schema={"name": "property_entitlement_limits", "description": "Read property-line entitlement for a workspace.", "parameters": {"type": "object", "properties": {"workspace_id": {"type": "string"}}}}, handler=property_entitlement_limits)
registry.register(name="property_domain_pack_get", toolset="property", schema={"name": "property_domain_pack_get", "description": "Read the configured property domain pack.", "parameters": {"type": "object", "properties": {}}}, handler=property_domain_pack_get)
