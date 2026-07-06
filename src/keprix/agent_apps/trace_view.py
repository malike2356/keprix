"""Agent app trace helpers for the agents runtime UI."""

from __future__ import annotations

from typing import Any

from keprix.agent_apps.run_store import get_run, list_run_events


def build_agent_app_trace_view(trace_id: str) -> dict[str, Any] | None:
    run = get_run(trace_id)
    if run is None:
        return None
    events = list_run_events(trace_id)
    formatted = [
        {
            "type": item["event"],
            "agent": run["app_name"],
            "payload": item["payload"],
            "at": item["created_at"],
        }
        for item in events
    ]
    return {
        "run_id": trace_id,
        "source": "agent_app",
        "app_name": run["app_name"],
        "current_agent": run["app_name"],
        "accepted_handoffs": [],
        "events": formatted,
        "summary": {
            "agent_events": sum(1 for event in formatted if event["type"] in {"before_run", "after_run"}),
            "handoffs": 0,
            "guardrails": 0,
            "tools": sum(1 for event in formatted if "tool" in event["type"]),
            "outputs": 1 if run.get("output") else 0,
        },
        "run": run,
    }
