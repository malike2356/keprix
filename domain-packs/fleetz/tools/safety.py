"""Fleet safety helpers: freshness gates, injection scrubbing, command deny."""

from __future__ import annotations

import re
from typing import Any

_INJECTION_RE = re.compile(
    r"(?:ignore\s+(?:previous|all)\s+instructions|system\s*prompt|you\s+are\s+now|"
    r"tool\s*call|execute\s+shell|immobilise|immobilize|cut\s+fuel|browse\s+to|"
    r"fetch\s+url|delete\s+all|</?\s*(?:system|tool|function)\b)",
    re.I,
)

_COMMAND_REQUEST_RE = re.compile(
    r"\b(?:immobilise|immobilize|cut\s+fuel|stop\s+engine|send\s+command|"
    r"flash\s+firmware|restart\s+tracker|disable\s+ignition)\b",
    re.I,
)

_ACCUSATION_RE = re.compile(
    r"\b(?:thief|stole|stealing|guilty|caught\s+stealing|definitely\s+theft)\b",
    re.I,
)

DEFAULT_MAX_AGE_S = 900.0  # 15 minutes for live operational conclusions
COMMAND_CAPABILITIES = (
    "vehicle_immobilise",
    "fuel_cut",
    "tracker_config",
    "firmware_update",
    "geofence_apply",
)


def treat_as_operator_text(text: str) -> dict[str, Any]:
    raw = str(text or "")
    matches = _INJECTION_RE.findall(raw)
    return {
        "text": raw,
        "treated_as": "operator_note_data",
        "injection_signals": list(
            {m.lower() if isinstance(m, str) else str(m).lower() for m in matches}
        ),
        "tool_instruction_allowed": False,
        "command_request_detected": bool(_COMMAND_REQUEST_RE.search(raw)),
    }


def refuse_if_stale(
    *,
    age_s: float | None,
    max_age_s: float = DEFAULT_MAX_AGE_S,
    sample_count: int = 0,
    quality_actionable: bool = True,
) -> dict[str, Any] | None:
    """Return a refusal payload when series is stale/insufficient; else None."""
    if sample_count <= 0:
        return {
            "status": "refused",
            "reason": "insufficient_series",
            "actionable": False,
            "definitive_conclusion": False,
            "operator_guidance": "Not enough samples to draw a definitive conclusion.",
        }
    if age_s is not None and age_s > max_age_s:
        return {
            "status": "refused",
            "reason": "stale_telemetry",
            "age_s": age_s,
            "max_age_s": max_age_s,
            "actionable": False,
            "definitive_conclusion": False,
            "operator_guidance": "Telemetry is stale; treat as non-actionable until refreshed.",
        }
    if not quality_actionable:
        return {
            "status": "refused",
            "reason": "low_sensor_quality",
            "actionable": False,
            "definitive_conclusion": False,
            "operator_guidance": "Sensor quality too low for definitive claims.",
        }
    return None


def strip_accusation_language(text: str) -> str:
    """Neutralise accusation wording; keep hypothesis framing."""
    out = str(text or "")
    out = _ACCUSATION_RE.sub("suspected anomaly", out)
    return out


def command_capability_status() -> dict[str, Any]:
    return {
        "vehicle_device_commands": "disabled",
        "capabilities": {name: "disabled" for name in COMMAND_CAPABILITIES},
        "reason": "Safety-critical control remains Fleetz product-owned; sidecar has no grant.",
        "traccar_command_api": False,
        "mqtt_command_publish": False,
        "tracker_tcp_udp": False,
    }


def assert_no_vehicle_command(capability: str) -> dict[str, Any] | None:
    bare = str(capability or "").removeprefix("fleetz.").removeprefix("fleetz_")
    if bare in COMMAND_CAPABILITIES or bare.startswith("vehicle_command"):
        return {
            "status": "error",
            "error": "vehicle_command_disabled",
            "capability": capability,
            "detail": command_capability_status(),
        }
    return None


def minimise_location(
    *,
    role: str,
    purpose: str,
    precise_points: list[dict[str, Any]] | None = None,
    allow_precise: bool = False,
) -> dict[str, Any]:
    """Drop precise routes unless role+purpose explicitly allow."""
    allowed = allow_precise and role in {"fleet_manager", "dispatcher", "owner"} and purpose in {
        "incident_investigation",
        "route_deviation_explain",
        "trip_report",
    }
    if allowed:
        return {"precise": True, "points": precise_points or [], "redacted": False}
    return {
        "precise": False,
        "points": [],
        "summary_only": True,
        "redacted": True,
        "reason": "location_minimised_for_role_purpose",
    }


def emergency_route_to_human(request_text: str) -> dict[str, Any]:
    return {
        "routed_to": "human_dispatch",
        "auto_vehicle_control": False,
        "message": "Emergency and vehicle-control requests must be handled by authorised humans.",
        "note_scan": treat_as_operator_text(request_text),
    }
