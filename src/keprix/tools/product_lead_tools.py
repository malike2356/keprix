"""Agent tools for product leads."""

from __future__ import annotations

import json
from typing import Any

from keprix.security.ai_hardening import record_anomaly, validate_tool_args
from keprix.tools.registry import registry

TOOLSET = "workspace_mesh"


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


def _handle_create(args: dict[str, Any], **kwargs: Any) -> str:
    schema = _schema(
        "create_lead",
        "",
        {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "contact_id": {"type": "string"},
            "campaign_id": {"type": "string"},
        },
        required=["name"],
    )["parameters"]
    errors = validate_tool_args(schema, args)
    if errors:
        record_anomaly("tool_schema_violation")
        return json.dumps({"error": "schema_violation", "details": errors})
    from keprix.product_leads.store import get_lead_store

    lead = get_lead_store().create(
        name=str(args["name"]),
        email=str(args.get("email") or ""),
        contact_id=args.get("contact_id"),
        campaign_id=args.get("campaign_id"),
    )
    return json.dumps(lead)


def _handle_list(args: dict[str, Any], **kwargs: Any) -> str:
    from keprix.product_leads.store import get_lead_store

    limit = int(args.get("limit") or 20)
    return json.dumps({"items": get_lead_store().list_leads(limit=limit)})


def _handle_link(args: dict[str, Any], **kwargs: Any) -> str:
    schema = {
        "type": "object",
        "properties": {
            "lead_id": {"type": "string"},
            "booking_id": {"type": "string"},
        },
        "required": ["lead_id", "booking_id"],
        "additionalProperties": False,
    }
    errors = validate_tool_args(schema, args)
    if errors:
        record_anomaly("tool_schema_violation")
        return json.dumps({"error": "schema_violation", "details": errors})
    from keprix.product_leads.store import get_lead_store

    try:
        lead = get_lead_store().link_booking(str(args["lead_id"]), str(args["booking_id"]))
    except LookupError as exc:
        return json.dumps({"error": str(exc)})
    return json.dumps(lead)


registry.register(
    name="create_lead",
    toolset=TOOLSET,
    schema=_schema(
        "create_lead",
        "Create a lightweight lead (not a full CRM). Optionally link contact_id.",
        {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "contact_id": {"type": "string"},
            "campaign_id": {"type": "string"},
        },
        required=["name"],
    ),
    handler=_handle_create,
)

registry.register(
    name="list_leads",
    toolset=TOOLSET,
    schema=_schema("list_leads", "List recent leads.", {"limit": {"type": "integer"}}),
    handler=_handle_list,
)

registry.register(
    name="link_booking_to_lead",
    toolset=TOOLSET,
    schema=_schema(
        "link_booking_to_lead",
        "Attach a viCal booking id to an existing lead.",
        {"lead_id": {"type": "string"}, "booking_id": {"type": "string"}},
        required=["lead_id", "booking_id"],
    ),
    handler=_handle_link,
)
