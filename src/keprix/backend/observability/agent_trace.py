"""Agent trace capture and local store (Prompt 57)."""

from __future__ import annotations

from typing import Any

from keprix.backend.evals.trace import AgentRunTrace, redact_dict
from keprix.backend.observability.cost_meter import record_cost
from keprix.backend.observability.token_meter import record_tokens


class AgentTraceStore:
    """In-memory trace store for local development and tests."""

    def __init__(self) -> None:
        self._traces: dict[str, AgentRunTrace] = {}

    def save(self, trace: AgentRunTrace) -> None:
        self._traces[trace.run_id] = trace

    def get(self, run_id: str) -> AgentRunTrace | None:
        return self._traces.get(run_id)

    def list_traces(self, *, limit: int = 50) -> list[dict[str, Any]]:
        items = sorted(
            self._traces.values(),
            key=lambda trace: trace.started_at,
            reverse=True,
        )
        return [trace.to_dict(redact=True) for trace in items[:limit]]

    def clear(self) -> None:
        self._traces.clear()


_trace_store: AgentTraceStore | None = None


def get_trace_store() -> AgentTraceStore:
    global _trace_store
    if _trace_store is None:
        _trace_store = AgentTraceStore()
    return _trace_store


def capture_trace(trace: AgentRunTrace) -> AgentRunTrace:
    if trace.tokens:
        record_tokens(trace.run_id, trace.tokens, workspace_id=trace.workspace_id)
    if trace.cost_estimate_usd:
        record_cost(trace.run_id, trace.cost_estimate_usd, workspace_id=trace.workspace_id)
    try:
        from keprix.usage.pricing_bridge import usage_from_counts
        from keprix.usage.recorder import get_llm_usage_recorder

        tokens = trace.tokens or {}
        usage = usage_from_counts(
            input_tokens=int(tokens.get("input", tokens.get("input_tokens", 0)) or 0),
            output_tokens=int(tokens.get("output", tokens.get("output_tokens", 0)) or 0),
            cache_read_tokens=int(tokens.get("cache_read", tokens.get("cache_read_tokens", 0)) or 0),
            cache_write_tokens=int(tokens.get("cache_write", tokens.get("cache_write_tokens", 0)) or 0),
        )
        if usage.total_tokens or trace.cost_estimate_usd:
            model = ""
            if trace.model_calls:
                model = str(trace.model_calls[-1].get("model") or "")
            get_llm_usage_recorder().record_sync(
                usage=usage,
                provider=str(trace.model_calls[-1].get("provider", "")) if trace.model_calls else "agent",
                model=model or "unknown",
                channel="trace",
                run_id=trace.run_id,
                workspace_id=trace.workspace_id,
                metadata={"outcome": trace.outcome},
                cost_result=None,
            )
    except Exception:
        pass
    get_trace_store().save(trace)
    return trace


def merge_runtime_trace(
    trace: AgentRunTrace,
    *,
    events: list[dict[str, Any]] | None = None,
) -> AgentRunTrace:
    for event in events or []:
        event_type = str(event.get("type") or "")
        payload = redact_dict(dict(event.get("payload") or {}))
        if event_type == "tool":
            trace.tool_calls.append(payload)
        elif event_type in {"agent_start", "agent_end", "handoff"}:
            trace.node_transitions.append({"type": event_type, **payload})
        elif event_type == "output":
            trace.artifacts.append(str(payload.get("text") or payload.get("artifact") or ""))
        elif event_type == "guardrail":
            trace.approvals.append(payload)
    return trace
