"""Observability dashboard and trace viewer API (Prompt 57 + data-ops P0)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from keprix.backend.observability.agent_trace import get_trace_store
from keprix.backend.observability.cost_meter import get_cost_meter
from keprix.backend.observability.otel import export_governance_trace, export_trace_otel, otel_configured
from keprix.backend.observability.token_meter import get_token_meter

router = APIRouter(prefix="/api/observability", tags=["observability"])


def _parse_iso(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _as_optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _trace_status(trace: dict[str, Any]) -> str:
    outcome = str(trace.get("outcome") or trace.get("status") or "unknown").lower()
    errors = trace.get("errors") or []
    if errors or outcome in {"error", "failed", "failure"}:
        return "error"
    if outcome in {"pending", "running"}:
        return "running"
    if outcome in {"ok", "success", "completed", "done"}:
        return "ok"
    return outcome or "unknown"


def _trace_agent(trace: dict[str, Any]) -> str:
    if trace.get("agent"):
        return str(trace["agent"])
    roles = trace.get("agent_roles") or []
    if isinstance(roles, list) and roles:
        return str(roles[0])
    return ""


def _trace_duration_ms(trace: dict[str, Any]) -> float | None:
    started = _parse_iso(str(trace.get("started_at") or "") or None)
    finished = _parse_iso(str(trace.get("finished_at") or "") or None)
    if started is None or finished is None:
        return None
    return max(0.0, (finished - started).total_seconds() * 1000.0)


def _enrich_trace(trace: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(trace)
    enriched["status"] = _trace_status(trace)
    enriched["agent"] = _trace_agent(trace)
    duration = _trace_duration_ms(trace)
    if duration is not None:
        enriched["duration_ms"] = round(duration, 2)
    return enriched


def _build_span_timeline(trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Synthetic span waterfall from node transitions, tools, and model calls."""
    spans: list[dict[str, Any]] = []
    started = _parse_iso(str(trace.get("started_at") or "") or None)
    base_ms = 0.0
    if started is not None:
        base_ms = started.timestamp() * 1000.0

    def add(kind: str, name: str, offset_ms: float, duration_ms: float, detail: Any = None) -> None:
        spans.append(
            {
                "kind": kind,
                "name": name,
                "offset_ms": round(offset_ms, 2),
                "duration_ms": round(max(1.0, duration_ms), 2),
                "detail": detail,
            }
        )

    cursor = 0.0
    for index, transition in enumerate(trace.get("node_transitions") or []):
        if not isinstance(transition, dict):
            continue
        label = str(transition.get("type") or transition.get("agent") or f"transition-{index}")
        add("node", label, cursor, 40.0, transition)
        cursor += 45.0

    for index, call in enumerate(trace.get("tool_calls") or []):
        if not isinstance(call, dict):
            continue
        label = str(call.get("name") or call.get("tool") or f"tool-{index}")
        add("tool", label, cursor, 80.0, call)
        cursor += 90.0

    for index, call in enumerate(trace.get("model_calls") or []):
        if not isinstance(call, dict):
            continue
        label = str(call.get("model") or call.get("provider") or f"model-{index}")
        add("model", label, cursor, 120.0, call)
        cursor += 130.0

    for index, err in enumerate(trace.get("errors") or []):
        add("error", f"error-{index}", cursor, 20.0, err)
        cursor += 25.0

    if not spans and base_ms:
        duration = _trace_duration_ms(trace) or 100.0
        add("run", "run", 0.0, duration, {"run_id": trace.get("run_id")})

    return spans


def _runtime_health(traces: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [d for d in (_trace_duration_ms(t) for t in traces) if d is not None]
    errors = sum(1 for t in traces if _trace_status(t) == "error")
    total = len(traces)
    p95 = None
    if durations:
        ordered = sorted(durations)
        idx = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
        p95 = round(ordered[idx], 2)
    avg = round(sum(durations) / len(durations), 2) if durations else None
    return {
        "trace_volume": total,
        "error_count": errors,
        "error_rate": round(errors / total, 4) if total else 0.0,
        "latency_avg_ms": avg,
        "latency_p95_ms": p95,
        "otel_configured": otel_configured(),
    }


@router.get("/dashboard")
async def observability_dashboard() -> dict[str, Any]:
    traces = [_enrich_trace(t) for t in get_trace_store().list_traces(limit=200)]
    payload: dict[str, Any] = {
        "cost": get_cost_meter().dashboard(),
        "tokens": get_token_meter().dashboard(),
        "trace_count": len(traces),
        "otel_configured": otel_configured(),
        "runtime": _runtime_health(traces),
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
async def list_traces(
    limit: int = Query(default=50, ge=1, le=500),
    status: str | None = Query(default=None),
    agent: str | None = Query(default=None),
    q: str | None = Query(default=None),
    since: str | None = Query(default=None),
    until: str | None = Query(default=None),
) -> dict[str, Any]:
    since_dt = _parse_iso(since if isinstance(since, str) else None)
    until_dt = _parse_iso(until if isinstance(until, str) else None)
    status_norm = _as_optional_str(status)
    if status_norm:
        status_norm = status_norm.lower()
    agent_norm = _as_optional_str(agent)
    if agent_norm:
        agent_norm = agent_norm.lower()
    query_norm = _as_optional_str(q)
    if query_norm:
        query_norm = query_norm.lower()
    limit_n = limit if isinstance(limit, int) else 50

    results: list[dict[str, Any]] = []
    for raw in get_trace_store().list_traces(limit=1000):
        trace = _enrich_trace(raw)
        started = _parse_iso(str(trace.get("started_at") or "") or None)
        if since_dt and started and started < since_dt:
            continue
        if until_dt and started and started > until_dt:
            continue
        if status_norm and _trace_status(trace) != status_norm:
            continue
        if agent_norm and agent_norm not in _trace_agent(trace).lower():
            continue
        if query_norm:
            hay = " ".join(
                [
                    str(trace.get("run_id") or ""),
                    str(trace.get("user_request") or ""),
                    str(trace.get("summary") or ""),
                    _trace_agent(trace),
                    _trace_status(trace),
                ]
            ).lower()
            if query_norm not in hay:
                continue
        results.append(trace)
        if len(results) >= limit_n:
            break

    return {"traces": results, "count": len(results)}


@router.get("/traces/{run_id}")
async def get_trace(run_id: str) -> dict[str, Any]:
    trace = get_trace_store().get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    payload = _enrich_trace(trace.to_dict(redact=True))
    payload["spans"] = _build_span_timeline(payload)
    return payload


@router.post("/traces/{run_id}/export")
async def export_trace(run_id: str) -> dict[str, Any]:
    trace = get_trace_store().get(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {
        "otel": export_trace_otel(trace),
        "governance": export_governance_trace(trace),
    }
