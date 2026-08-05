"""Incident response drill simulation."""

from __future__ import annotations

import time
from typing import Any

from keprix.incident.severity import IncidentLevel
from keprix.incident.response import declare_incident, note_incident_event
from keprix.security.auto_response import reset_auto_response_state


def run_drill(*, level: str = "l3") -> dict[str, Any]:
    reset_auto_response_state()
    started = time.perf_counter()
    incident_level = IncidentLevel.from_label(level)
    result = declare_incident(
        level=incident_level,
        reason="incident_response_drill",
        product_id="keprix",
        session_id="drill-session",
    )
    incident_id = result["incident"]["id"]
    note_incident_event(incident_id, "drill_complete", "Simulated containment finished")
    elapsed = round(time.perf_counter() - started, 2)
    target_seconds = 15 if incident_level == IncidentLevel.L3_CRITICAL else 120
    return {
        "ok": elapsed <= target_seconds,
        "level": incident_level.value,
        "elapsed_seconds": elapsed,
        "target_seconds": target_seconds,
        "incident_id": incident_id,
        "actions": result.get("actions") or [],
    }
