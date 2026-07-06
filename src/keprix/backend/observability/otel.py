"""OpenTelemetry export when configured (Prompt 57)."""

from __future__ import annotations

import json
import os
from typing import Any

from keprix.backend.evals.trace import AgentRunTrace


def otel_configured() -> bool:
    return bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("KEPRIX_OTEL_ENDPOINT"))


def export_trace_otel(trace: AgentRunTrace) -> dict[str, Any]:
    """Export trace span payload; uses HTTP POST when endpoint is configured."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("KEPRIX_OTEL_ENDPOINT")
    payload = {
        "resourceSpans": [
            {
                "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "keprix"}}]},
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": trace.run_id.replace("-", "")[:32],
                                "spanId": trace.run_id.replace("-", "")[-16:],
                                "name": f"agent.run.{trace.outcome}",
                                "attributes": [
                                    {"key": "workspace_id", "value": {"stringValue": trace.workspace_id}},
                                    {"key": "cost_usd", "value": {"doubleValue": trace.cost_estimate_usd}},
                                ],
                                "events": [
                                    {"name": "tool_call", "attributes": []}
                                    for _ in trace.tool_calls[:20]
                                ],
                            }
                        ]
                    }
                ],
            }
        ],
        "keprix_trace": trace.to_dict(redact=True),
    }
    if not endpoint:
        return {"exported": False, "reason": "OTEL not configured", "payload": payload}
    try:
        import urllib.request

        req = urllib.request.Request(
            endpoint.rstrip("/") + "/v1/traces",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return {"exported": True, "status": response.status}
    except Exception as exc:
        return {"exported": False, "reason": str(exc), "payload": payload}


def export_governance_trace(trace: AgentRunTrace) -> dict[str, Any]:
    """Bridge trace summary to the governance provider when KEPRIX_GOVERNANCE_TRACE_EXPORT is enabled."""
    if os.environ.get("KEPRIX_GOVERNANCE_TRACE_EXPORT", "").lower() not in {"1", "true", "yes"}:
        return {"exported": False, "reason": "Governance trace export not configured"}
    try:
        from keprix.governance.client import get_governance_client

        client = get_governance_client()
        summary = {
            "run_id": trace.run_id,
            "workspace_id": trace.workspace_id,
            "outcome": trace.outcome,
            "cost_usd": trace.cost_estimate_usd,
            "tokens": trace.tokens,
            "errors": trace.errors,
        }
        return {"exported": True, "summary": summary, "governance_status": client.__class__.__name__}
    except Exception as exc:
        return {"exported": False, "reason": str(exc)}
