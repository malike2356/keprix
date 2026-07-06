"""Agent trace observability tests (Prompt 57)."""

from __future__ import annotations

import pytest

from keprix.backend.evals.trace import AgentRunTrace
from keprix.backend.observability.agent_trace import capture_trace, get_trace_store, merge_runtime_trace
from keprix.backend.observability.cost_meter import get_cost_meter
from keprix.backend.observability.token_meter import get_token_meter


def test_agent_trace_capture_and_redaction():
    store = get_trace_store()
    store.clear()
    get_cost_meter().clear()
    get_token_meter().clear()

    trace = AgentRunTrace.start(
        workspace_id="ws-1",
        user_request="Summarize docs",
        agent_roles=["researcher"],
    )
    trace.tool_calls.append({"name": "search", "api_key": "sk-secret12345678901234567890"})
    trace.tokens = {"input": 100, "output": 50}
    trace.cost_estimate_usd = 0.02
    trace.finish("success")

    capture_trace(trace)
    stored = store.get(trace.run_id)
    assert stored is not None
    payload = stored.to_dict(redact=True)
    assert payload["tool_calls"][0]["api_key"] == "[REDACTED]"
    assert get_cost_meter().total() == pytest.approx(0.02)
    assert get_token_meter().totals()["input"] == 100


def test_merge_runtime_trace_events():
    trace = AgentRunTrace.start(workspace_id="ws-2", user_request="Browse page")
    merge_runtime_trace(
        trace,
        events=[
            {"type": "tool", "payload": {"name": "browser.navigate", "url": "https://example.com"}},
            {"type": "output", "payload": {"artifact": "page_title.txt"}},
            {"type": "guardrail", "payload": {"approved": True, "token": "secret"}},
        ],
    )
    assert len(trace.tool_calls) == 1
    assert trace.artifacts == ["page_title.txt"]
    assert trace.approvals[0]["token"] == "[REDACTED]"
