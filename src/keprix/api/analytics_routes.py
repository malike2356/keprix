"""Analytics API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from keprix.api.auth import require_api_auth
from keprix.observability import insights as insights_api
from keprix.observability.metrics import get_metrics_store

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/usage")
async def usage_summary(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    summary = insights_api.usage_summary(days=days)
    store = get_metrics_store()
    summary["daily_tokens"] = await store.sum_by_day(metric_type="token", days=days)
    summary["daily_messages"] = await store.sum_by_day(metric_type="message", days=days)
    return summary


@router.get("/providers")
async def provider_breakdown(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    store = get_metrics_store()
    breakdown = await store.breakdown(metric_type="provider_request", days=days)
    rate_limits = await store.rate_limit_events(days=days)
    return {"providers": breakdown, "rate_limit_events": rate_limits}


@router.get("/costs")
async def cost_estimates(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    summary = insights_api.usage_summary(days=days)
    return {
        "days": days,
        "estimated_cost_usd": summary.get("estimated_cost_usd", 0.0),
        "currency": "USD",
        "note": "Costs estimated from published token prices in usage_pricing.",
    }


@router.get("/tools")
async def tool_usage(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    store = get_metrics_store()
    tools = await store.breakdown(metric_type="tool_call", days=days)
    return {"tools": tools}


@router.get("/skills")
async def skill_usage(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    store = get_metrics_store()
    skills = await store.breakdown(metric_type="skill_run", days=days)
    return {"skills": skills}


@router.get("/timeline")
async def usage_timeline(
    _user: str = Depends(require_api_auth),
    days: int = Query(default=30, ge=1, le=90),
) -> dict:
    return await insights_api.timeline_from_metrics(days=days)
