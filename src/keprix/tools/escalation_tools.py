"""Keprix tools: Aiva human VA escalation (K05)."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry

TOOLSET = "escalation"


def check_escalation_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _svc():
    from keprix.aiva_escalation.service import get_escalation_service

    return get_escalation_service()


def escalation_create(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    original_input = str(args.get("original_input") or args.get("input") or "").strip()
    if not workspace_id or not worker_id or not original_input:
        return _err("workspace_id, worker_id, and original_input are required")
    try:
        result = _svc().create(
            workspace_id=workspace_id,
            worker_id=worker_id,
            original_input=original_input,
            escalation_type=str(args.get("escalation_type") or "low_confidence"),
            confidence_score=args.get("confidence_score"),
            session_id=args.get("session_id"),
            holding_message=args.get("holding_message"),
            channel=args.get("channel"),
            notify=args.get("notify", True) is not False,
        )
    except ValueError as exc:
        return _err(str(exc))
    return _ok(result)


def escalation_assign(args: dict[str, Any], **kwargs: Any) -> str:
    escalation_id = str(args.get("escalation_id") or "").strip()
    assigned_va = str(args.get("assigned_va") or "").strip()
    if not escalation_id or not assigned_va:
        return _err("escalation_id and assigned_va are required")
    try:
        row = _svc().assign(escalation_id, assigned_va)
    except LookupError as exc:
        return _err(str(exc))
    return _ok({"escalation": row})


def escalation_complete(args: dict[str, Any], **kwargs: Any) -> str:
    escalation_id = str(args.get("escalation_id") or "").strip()
    va_response = str(args.get("va_response") or args.get("response") or "").strip()
    if not escalation_id or not va_response:
        return _err("escalation_id and va_response are required")
    try:
        row = _svc().complete(escalation_id, va_response, assigned_va=args.get("assigned_va"))
    except (LookupError, ValueError) as exc:
        return _err(str(exc))
    return _ok({"escalation": row, "user_visible_response": row.get("va_response")})


def escalation_get_queue(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    status = args.get("status", "pending")
    limit = int(args.get("limit") or 50)
    return _ok(_svc().get_queue(workspace_id, status=status, limit=limit))


def human_assist_request(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    worker_id = str(args.get("worker_id") or "").strip()
    reason = str(args.get("reason") or "").strip()
    if not workspace_id or not worker_id or not reason:
        return _err("workspace_id, worker_id, and reason are required")
    result = _svc().human_assist_request(
        workspace_id=workspace_id,
        worker_id=worker_id,
        reason=reason,
        urgency=str(args.get("urgency") or "normal"),
        details=args.get("details"),
        original_input=args.get("original_input"),
        session_id=args.get("session_id"),
    )
    return _ok(result)


def escalation_process_timeouts(args: dict[str, Any], **kwargs: Any) -> str:
    minutes = args.get("timeout_minutes")
    result = _svc().process_timeouts(timeout_minutes=int(minutes) if minutes is not None else None)
    return _ok(result)


registry.register(
    name="escalation_create",
    toolset=TOOLSET,
    schema={
        "name": "escalation_create",
        "description": "Create a human VA escalation when AI confidence is low or scope is exceeded.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "original_input": {"type": "string"},
                "escalation_type": {
                    "type": "string",
                    "enum": ["low_confidence", "out_of_scope", "manual_request", "safety_flag"],
                },
                "confidence_score": {"type": "number"},
                "session_id": {"type": "string"},
                "holding_message": {"type": "string"},
                "channel": {"type": "string"},
                "notify": {"type": "boolean"},
            },
            "required": ["workspace_id", "worker_id", "original_input"],
        },
    },
    handler=escalation_create,
    check_fn=check_escalation_requirements,
)

registry.register(
    name="escalation_assign",
    toolset=TOOLSET,
    schema={
        "name": "escalation_assign",
        "description": "Assign a pending escalation to a human VA.",
        "parameters": {
            "type": "object",
            "properties": {
                "escalation_id": {"type": "string"},
                "assigned_va": {"type": "string"},
            },
            "required": ["escalation_id", "assigned_va"],
        },
    },
    handler=escalation_assign,
    check_fn=check_escalation_requirements,
)

registry.register(
    name="escalation_complete",
    toolset=TOOLSET,
    schema={
        "name": "escalation_complete",
        "description": "Complete an escalation with the human VA response (flows back to the user).",
        "parameters": {
            "type": "object",
            "properties": {
                "escalation_id": {"type": "string"},
                "va_response": {"type": "string"},
                "assigned_va": {"type": "string"},
            },
            "required": ["escalation_id", "va_response"],
        },
    },
    handler=escalation_complete,
    check_fn=check_escalation_requirements,
)

registry.register(
    name="escalation_get_queue",
    toolset=TOOLSET,
    schema={
        "name": "escalation_get_queue",
        "description": "List escalations for a workspace (dashboard queue).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["workspace_id"],
        },
    },
    handler=escalation_get_queue,
    check_fn=check_escalation_requirements,
)

registry.register(
    name="human_assist_request",
    toolset=TOOLSET,
    schema={
        "name": "human_assist_request",
        "description": "Manual human assist request from the user or worker.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "reason": {"type": "string"},
                "urgency": {"type": "string", "enum": ["normal", "urgent"]},
                "details": {"type": "string"},
                "original_input": {"type": "string"},
                "session_id": {"type": "string"},
            },
            "required": ["workspace_id", "worker_id", "reason"],
        },
    },
    handler=human_assist_request,
    check_fn=check_escalation_requirements,
)

registry.register(
    name="escalation_process_timeouts",
    toolset=TOOLSET,
    schema={
        "name": "escalation_process_timeouts",
        "description": "Reassign escalations that timed out without a VA pickup.",
        "parameters": {
            "type": "object",
            "properties": {"timeout_minutes": {"type": "integer"}},
        },
    },
    handler=escalation_process_timeouts,
    check_fn=check_escalation_requirements,
)
