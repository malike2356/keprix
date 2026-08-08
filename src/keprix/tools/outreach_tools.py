"""Keprix tools: outreach automation (K02)."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry

TOOLSET = "outreach"


def check_outreach_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _svc():
    from keprix.outreach.service import get_outreach_service

    return get_outreach_service()


def outreach_create_campaign(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    name = str(args.get("name") or "").strip()
    if not workspace_id or not name:
        return _err("workspace_id and name are required")
    campaign = _svc().create_campaign(
        workspace_id,
        name,
        status=args.get("status"),
        source_type=args.get("source_type"),
        daily_cap=args.get("daily_cap"),
        timezone=args.get("timezone"),
        business_hours_only=args.get("business_hours_only"),
        warmup_days=args.get("warmup_days"),
        require_approval=args.get("require_approval"),
        default_sequence_id=args.get("default_sequence_id"),
        default_booking_link=args.get("default_booking_link"),
    )
    return _ok({"campaign": campaign})


def outreach_create_sequence(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    name = str(args.get("name") or "").strip()
    steps = args.get("steps")
    if not workspace_id or not name:
        return _err("workspace_id and name are required")
    if not isinstance(steps, list) or len(steps) < 1:
        return _err("steps must be a non-empty array")
    try:
        sequence = _svc().create_sequence(
            workspace_id,
            name,
            steps=steps,
            channel_default=args.get("channel_default"),
            stop_on_reply=args.get("stop_on_reply"),
            stop_on_booking=args.get("stop_on_booking"),
            stop_on_unsubscribe=args.get("stop_on_unsubscribe"),
        )
    except ValueError as exc:
        return _err(str(exc))
    return _ok({"sequence": sequence})


def outreach_add_leads(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    leads = args.get("leads")
    csv_text = args.get("csv_text") or args.get("csv")
    if not leads and not csv_text:
        return _err("leads or csv_text is required")
    result = _svc().add_leads(
        workspace_id,
        leads=leads if isinstance(leads, list) else None,
        csv_text=str(csv_text) if csv_text else None,
        campaign_id=args.get("campaign_id"),
    )
    return _ok(result)


def outreach_enroll_lead(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    lead_id = str(args.get("lead_id") or "").strip()
    sequence_id = str(args.get("sequence_id") or "").strip()
    if not workspace_id or not lead_id or not sequence_id:
        return _err("workspace_id, lead_id, and sequence_id are required")
    try:
        result = _svc().enroll_lead(
            workspace_id,
            lead_id,
            sequence_id,
            start_immediately=args.get("start_immediately", True) is not False,
        )
    except LookupError as exc:
        return _err(str(exc))
    return _ok(result)


def outreach_process_due(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = args.get("workspace_id")
    limit = int(args.get("limit") or 50)
    dry_run = args.get("dry_run")
    result = _svc().process_due(
        str(workspace_id) if workspace_id else None,
        limit=limit,
        dry_run=None if dry_run is None else bool(dry_run),
    )
    return _ok(result)


def outreach_classify_reply(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    body = str(args.get("body") or "")
    from_address = str(args.get("from_address") or args.get("from") or "").strip()
    if not workspace_id or not body or not from_address:
        return _err("workspace_id, from_address, and body are required")
    try:
        result = _svc().classify_and_apply_reply(
            workspace_id,
            from_address=from_address,
            body=body,
            subject=str(args.get("subject") or ""),
            lead_id=args.get("lead_id"),
            message_id=args.get("message_id"),
            classification=args.get("classification"),
            confidence=args.get("confidence"),
        )
    except LookupError as exc:
        return _err(str(exc))
    return _ok(result)


def outreach_move_lead(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    lead_id = str(args.get("lead_id") or "").strip()
    status = str(args.get("status") or "").strip()
    if not workspace_id or not lead_id or not status:
        return _err("workspace_id, lead_id, and status are required")
    try:
        lead = _svc().move_lead(workspace_id, lead_id, status)
    except (LookupError, ValueError) as exc:
        return _err(str(exc))
    return _ok({"lead": lead})


def outreach_get_pipeline(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    return _ok(_svc().get_pipeline(workspace_id, args.get("campaign_id")))


def outreach_get_campaign_stats(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    campaign_id = str(args.get("campaign_id") or "").strip()
    if not workspace_id or not campaign_id:
        return _err("workspace_id and campaign_id are required")
    return _ok(_svc().get_campaign_stats(workspace_id, campaign_id))


def outreach_daily_digest(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    hours = int(args.get("hours") or 24)
    return _ok(_svc().daily_digest(workspace_id, hours=hours))


def outreach_scan_replies(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = args.get("workspace_id")
    return _ok(_svc().scan_replies(str(workspace_id) if workspace_id else None))


registry.register(
    name="outreach_create_campaign",
    toolset=TOOLSET,
    schema={
        "name": "outreach_create_campaign",
        "description": "Create an outreach campaign (draft/active/paused).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "name": {"type": "string"},
                "status": {"type": "string"},
                "source_type": {"type": "string"},
                "daily_cap": {"type": "integer"},
                "timezone": {"type": "string"},
                "business_hours_only": {"type": "boolean"},
                "warmup_days": {"type": "integer"},
                "require_approval": {"type": "boolean"},
                "default_sequence_id": {"type": "string"},
                "default_booking_link": {"type": "string"},
            },
            "required": ["workspace_id", "name"],
        },
    },
    handler=outreach_create_campaign,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_create_sequence",
    toolset=TOOLSET,
    schema={
        "name": "outreach_create_sequence",
        "description": "Create a multi-step outreach sequence (3+ steps recommended).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "name": {"type": "string"},
                "channel_default": {"type": "string"},
                "stop_on_reply": {"type": "boolean"},
                "stop_on_booking": {"type": "boolean"},
                "stop_on_unsubscribe": {"type": "boolean"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_order": {"type": "integer"},
                            "channel": {"type": "string"},
                            "subject": {"type": "string"},
                            "body": {"type": "string"},
                            "cta": {"type": "string"},
                            "link": {"type": "string"},
                            "delay_hours": {"type": "integer"},
                        },
                        "required": ["body"],
                    },
                },
            },
            "required": ["workspace_id", "name", "steps"],
        },
    },
    handler=outreach_create_sequence,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_add_leads",
    toolset=TOOLSET,
    schema={
        "name": "outreach_add_leads",
        "description": "Add leads (JSON array or CSV text) to a workspace/campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_id": {"type": "string"},
                "leads": {"type": "array", "items": {"type": "object"}},
                "csv_text": {"type": "string"},
            },
            "required": ["workspace_id"],
        },
    },
    handler=outreach_add_leads,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_enroll_lead",
    toolset=TOOLSET,
    schema={
        "name": "outreach_enroll_lead",
        "description": "Enroll a lead in a sequence.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "lead_id": {"type": "string"},
                "sequence_id": {"type": "string"},
                "start_immediately": {"type": "boolean"},
            },
            "required": ["workspace_id", "lead_id", "sequence_id"],
        },
    },
    handler=outreach_enroll_lead,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_process_due",
    toolset=TOOLSET,
    schema={
        "name": "outreach_process_due",
        "description": "Process due sequence steps (cron: every 5 minutes).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "limit": {"type": "integer"},
                "dry_run": {"type": "boolean"},
            },
        },
    },
    handler=outreach_process_due,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_classify_reply",
    toolset=TOOLSET,
    schema={
        "name": "outreach_classify_reply",
        "description": "Classify an inbound reply and update pipeline / enrollments.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "from_address": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "lead_id": {"type": "string"},
                "message_id": {"type": "string"},
                "classification": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["workspace_id", "from_address", "body"],
        },
    },
    handler=outreach_classify_reply,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_move_lead",
    toolset=TOOLSET,
    schema={
        "name": "outreach_move_lead",
        "description": "Move a lead between pipeline stages.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "lead_id": {"type": "string"},
                "status": {"type": "string"},
            },
            "required": ["workspace_id", "lead_id", "status"],
        },
    },
    handler=outreach_move_lead,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_get_pipeline",
    toolset=TOOLSET,
    schema={
        "name": "outreach_get_pipeline",
        "description": "Get pipeline board counts by lead status.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_id": {"type": "string"},
            },
            "required": ["workspace_id"],
        },
    },
    handler=outreach_get_pipeline,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_get_campaign_stats",
    toolset=TOOLSET,
    schema={
        "name": "outreach_get_campaign_stats",
        "description": "Stats for an outreach campaign (leads, sends, replies, pipeline).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_id": {"type": "string"},
            },
            "required": ["workspace_id", "campaign_id"],
        },
    },
    handler=outreach_get_campaign_stats,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_daily_digest",
    toolset=TOOLSET,
    schema={
        "name": "outreach_daily_digest",
        "description": "Daily digest of new leads, replies, and bookings.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "hours": {"type": "integer"},
            },
            "required": ["workspace_id"],
        },
    },
    handler=outreach_daily_digest,
    check_fn=check_outreach_requirements,
)

registry.register(
    name="outreach_scan_replies",
    toolset=TOOLSET,
    schema={
        "name": "outreach_scan_replies",
        "description": "Scan inbox for outreach replies (cron every 2m).",
        "parameters": {
            "type": "object",
            "properties": {"workspace_id": {"type": "string"}},
        },
    },
    handler=outreach_scan_replies,
    check_fn=check_outreach_requirements,
)
