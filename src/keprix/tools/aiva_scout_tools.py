"""Keprix tools: scout_filter_prompt, scout_log_event, scout_check_kill, scout_heartbeat."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from tools.registry import registry


def check_aiva_scout_requirements() -> bool:
    return True


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


def scout_filter_prompt(
    workspace_id: str,
    prompt: str,
    session_id: str | None = None,
    model: str | None = None,
) -> str:
    from keprix.security.aiva_scout import get_aiva_scout_guard

    result = _run_async(
        get_aiva_scout_guard().filter_prompt(
            workspace_id=workspace_id,
            prompt=prompt,
            session_id=session_id,
            model=model,
        )
    )
    return json.dumps(
        {
            "blocked": result.blocked,
            "verdict": result.verdict,
            "risk_score": result.risk_score,
            "reason": result.reason,
        },
        ensure_ascii=False,
    )


def scout_log_event(
    workspace_id: str,
    event_type: str,
    session_id: str | None = None,
    tool_name: str | None = None,
    tool_args: Any = None,
    tool_result: Any = None,
    response: str | None = None,
    model: str | None = None,
) -> str:
    from keprix.security.aiva_scout import get_aiva_scout_guard

    result = _run_async(
        get_aiva_scout_guard().log_event(
            workspace_id=workspace_id,
            event_type=event_type,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            tool_result=tool_result,
            response=response,
            model=model,
        )
    )
    return json.dumps(result, ensure_ascii=False, default=str)


def scout_check_kill(workspace_id: str | None = None) -> str:
    from keprix.security.aiva_scout import get_aiva_scout_guard

    status = get_aiva_scout_guard().check_kill(workspace_id)
    return json.dumps(
        {
            "active": status.active,
            "scope": status.scope,
            "workspace_id": status.workspace_id,
            "reason": status.reason,
            "activated_by": status.activated_by,
            "activated_at": status.activated_at,
        },
        ensure_ascii=False,
    )


def scout_heartbeat(workspace_id: str | None = None) -> str:
    from keprix.security.aiva_scout import get_aiva_scout_guard

    result = _run_async(get_aiva_scout_guard().heartbeat(workspace_id=workspace_id))
    return json.dumps(result, ensure_ascii=False, default=str)


registry.register(
    name="scout_filter_prompt",
    toolset="scout",
    schema={
        "name": "scout_filter_prompt",
        "description": "Send a prompt to Labyrinth Scout for injection / policy check before LLM execution.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "prompt": {"type": "string"},
                "session_id": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["workspace_id", "prompt"],
        },
    },
    handler=lambda args, **kw: scout_filter_prompt(
        workspace_id=str(args.get("workspace_id") or ""),
        prompt=str(args.get("prompt") or ""),
        session_id=args.get("session_id"),
        model=args.get("model"),
    ),
    check_fn=check_aiva_scout_requirements,
)

registry.register(
    name="scout_log_event",
    toolset="scout",
    schema={
        "name": "scout_log_event",
        "description": "Log a tool call or agent response event to Labyrinth Scout.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "event_type": {
                    "type": "string",
                    "enum": ["tool_call", "agent_response", "anomaly"],
                },
                "session_id": {"type": "string"},
                "tool_name": {"type": "string"},
                "tool_args": {"type": "object"},
                "tool_result": {},
                "response": {"type": "string"},
                "model": {"type": "string"},
            },
            "required": ["workspace_id", "event_type"],
        },
    },
    handler=lambda args, **kw: scout_log_event(
        workspace_id=str(args.get("workspace_id") or ""),
        event_type=str(args.get("event_type") or ""),
        session_id=args.get("session_id"),
        tool_name=args.get("tool_name"),
        tool_args=args.get("tool_args"),
        tool_result=args.get("tool_result"),
        response=args.get("response"),
        model=args.get("model"),
    ),
    check_fn=check_aiva_scout_requirements,
)

registry.register(
    name="scout_check_kill",
    toolset="scout",
    schema={
        "name": "scout_check_kill",
        "description": "Check whether Scout kill switch is active for a workspace or globally.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
            },
        },
    },
    handler=lambda args, **kw: scout_check_kill(
        workspace_id=(str(args.get("workspace_id")) if args.get("workspace_id") else None),
    ),
    check_fn=check_aiva_scout_requirements,
)

registry.register(
    name="scout_heartbeat",
    toolset="scout",
    schema={
        "name": "scout_heartbeat",
        "description": "Send a Scout health heartbeat and report Keprix sensor catalog.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
            },
        },
    },
    handler=lambda args, **kw: scout_heartbeat(
        workspace_id=(str(args.get("workspace_id")) if args.get("workspace_id") else None),
    ),
    check_fn=check_aiva_scout_requirements,
)
