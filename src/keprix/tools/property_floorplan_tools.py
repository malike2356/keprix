"""Agent tools for floor-plan proposals and deterministic checks."""

from __future__ import annotations

import json

from keprix.property_floorplan.compliance import check
from keprix.property_floorplan.refurb import guidance
from keprix.property_floorplan.vision import analyze_image
from keprix.tools.registry import registry


def floor_plan_analyze(args: dict) -> str:
    return json.dumps(analyze_image(str(args.get("image_path") or ""), mode=str(args.get("mode") or "boq"), model=args.get("model")), default=str)


def floor_plan_compliance_check(args: dict) -> str:
    rooms = args.get("rooms") or []
    if not isinstance(rooms, list) or not rooms:
        return json.dumps({"status": "invalid", "reason": "rooms is required"})
    return json.dumps(check(rooms, str(args.get("property_type") or "hmo")), default=str)


registry.register(name="floor_plan_analyze", toolset="property", schema={"name": "floor_plan_analyze", "description": "Analyze a floor-plan image using the configured vision provider; returns a proposal for confirmation.", "parameters": {"type": "object", "properties": {"image_path": {"type": "string"}, "mode": {"type": "string", "enum": ["compliance", "boq"]}, "model": {"type": "string"}}, "required": ["image_path"]}}, handler=floor_plan_analyze)
registry.register(name="floor_plan_compliance_check", toolset="property", schema={"name": "floor_plan_compliance_check", "description": "Run deterministic HMO room-size checks on confirmed rooms.", "parameters": {"type": "object", "properties": {"property_type": {"type": "string"}, "rooms": {"type": "array"}}, "required": ["rooms"]}}, handler=floor_plan_compliance_check)
