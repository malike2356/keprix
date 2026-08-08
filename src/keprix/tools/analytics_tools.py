"""Keprix tools: Aiva analytics (K04)."""

from __future__ import annotations

import json
from typing import Any

from tools.registry import registry

TOOLSET = "analytics"


def check_analytics_requirements() -> bool:
    return True


def _ok(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _svc():
    from keprix.aiva_analytics.service import get_analytics_service

    return get_analytics_service()


def analytics_overview(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    days = int(args.get("days") or 30)
    return _ok(_svc().overview(workspace_id, days=days))


def analytics_outreach(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    return _ok(
        _svc().outreach(
            workspace_id,
            campaign_id=args.get("campaign_id"),
            days=int(args.get("days") or 30),
        )
    )


def analytics_worker(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    return _ok(
        _svc().worker(
            workspace_id,
            worker_id=args.get("worker_id"),
            days=int(args.get("days") or 30),
        )
    )


def analytics_usage(args: dict[str, Any], **kwargs: Any) -> str:
    workspace_id = str(args.get("workspace_id") or "").strip()
    if not workspace_id:
        return _err("workspace_id is required")
    return _ok(_svc().usage(workspace_id, days=int(args.get("days") or 30)))


def analytics_aggregate_daily(args: dict[str, Any], **kwargs: Any) -> str:
    lookback = int(args.get("lookback_days") or 2)
    return _ok(_svc().aggregate_daily(lookback_days=lookback))


registry.register(
    name="analytics_overview",
    toolset=TOOLSET,
    schema={
        "name": "analytics_overview",
        "description": "Top-level Aiva KPIs for a workspace (agent, outreach, workers).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["workspace_id"],
        },
    },
    handler=analytics_overview,
    check_fn=check_analytics_requirements,
)

registry.register(
    name="analytics_outreach",
    toolset=TOOLSET,
    schema={
        "name": "analytics_outreach",
        "description": "Outreach funnel metrics for a workspace or campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "campaign_id": {"type": "string"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["workspace_id"],
        },
    },
    handler=analytics_outreach,
    check_fn=check_analytics_requirements,
)

registry.register(
    name="analytics_worker",
    toolset=TOOLSET,
    schema={
        "name": "analytics_worker",
        "description": "Per-worker Aiva stats (messages, escalations, tokens).",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "worker_id": {"type": "string"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["workspace_id"],
        },
    },
    handler=analytics_worker,
    check_fn=check_analytics_requirements,
)

registry.register(
    name="analytics_usage",
    toolset=TOOLSET,
    schema={
        "name": "analytics_usage",
        "description": "Token and cost usage series for a workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["workspace_id"],
        },
    },
    handler=analytics_usage,
    check_fn=check_analytics_requirements,
)

registry.register(
    name="analytics_aggregate_daily",
    toolset=TOOLSET,
    schema={
        "name": "analytics_aggregate_daily",
        "description": "Roll up recent Aiva metrics into daily summary rows.",
        "parameters": {
            "type": "object",
            "properties": {
                "lookback_days": {"type": "integer", "default": 2},
            },
        },
    },
    handler=analytics_aggregate_daily,
    check_fn=check_analytics_requirements,
)
