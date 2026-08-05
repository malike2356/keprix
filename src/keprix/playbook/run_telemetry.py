"""Build Scout playbook run telemetry payloads."""

from __future__ import annotations

from typing import Any

from keprix.playbook.runtime.state import PlaybookRun


def enrich_run_completion(
    run: PlaybookRun,
    *,
    playbook_id: str | None,
    version_hash: str | None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a terminal run payload for Scout lifecycle telemetry."""
    event_rows = events or []
    connector_ids = sorted(
        {
            str(event.get("payload", {}).get("connector_id"))
            for event in event_rows
            if event.get("payload", {}).get("connector_id")
        }
    )
    completed = [event for event in event_rows if event.get("event_type") == "playbook.node.completed"]
    duration_ms = sum(
        int(event.get("payload", {}).get("duration_ms") or 0)
        for event in completed
    )
    return {
        "playbook_id": playbook_id or run.graph_id,
        "run_id": run.run_id,
        "version_hash": version_hash,
        "status": run.status.value,
        "duration_ms": duration_ms,
        "cost_usd": None,
        "step_count": len(completed),
        "connector_ids_used": connector_ids,
    }
