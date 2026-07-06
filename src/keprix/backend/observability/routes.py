"""Observability dashboard and trace viewer API (Prompt 57)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from keprix.backend.observability.agent_trace import get_trace_store
from keprix.backend.observability.cost_meter import get_cost_meter
from keprix.backend.observability.otel import export_governance_trace, export_trace_otel, otel_configured
from keprix.backend.observability.token_meter import get_token_meter

router = APIRouter(prefix="/api/observability", tags=["observability"])


@router.get("/dashboard", deprecated=True)
async def observability_dashboard() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "cost": get_cost_meter().dashboard(),
        "tokens": get_token_meter().dashboard(),
        "trace_count": len(get_trace_store().list_traces(limit=1000)),
        "otel_configured": otel_configured(),
    }
    try:
        from keprix.usage.analytics import get_llm_usage_analytics
        from keprix.usage.filters import UsageQueryFilters

        payload["usage_summary"] = await get_llm_usage_analytics().summary(
            UsageQueryFilters(days=7)
        )
    except Exception:
        payload["usage_summary"] = None
    return payload


@router.get("/traces")
async def list_traces(limit: int = 50) -> dict[str, Any]:
    return {"traces": get_trace_store().list_traces(limit=limit)}


@router.get("/traces/{run_id}")
async def get_trace(run_id: str) -> dict[str, Any]:
    trace = get_trace_store().get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace.to_dict(redact=True)


@router.post("/traces/{run_id}/export")
async def export_trace(run_id: str) -> dict[str, Any]:
    trace = get_trace_store().get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {
        "otel": export_trace_otel(trace),
        "governance": export_governance_trace(trace),
    }
