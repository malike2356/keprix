"""Fleetz product pack node catalog for the shared product_sidecar registry."""

from __future__ import annotations

from keprix.product_sidecar.types import CapabilityNode, NodeStatus, RiskClass

_RISK = {
    "read": RiskClass.READ,
    "propose": RiskClass.PROPOSE,
    "mutate": RiskClass.MUTATE,
    "outbound": RiskClass.OUTBOUND,
    "destructive": RiskClass.DESTRUCTIVE,
    "high_risk": RiskClass.HIGH_RISK,
}

_STATUS = {
    "live": NodeStatus.LIVE,
    "stub": NodeStatus.STUB,
    "not_configured": NodeStatus.NOT_CONFIGURED,
    "disabled": NodeStatus.DISABLED,
    "degraded": NodeStatus.DEGRADED,
}

# Mirrors domain-packs/fleetz capability surface (advisory; commands disabled).
_SPECS: list[tuple[str, str, str, str, str, bool]] = [
    # key, title, domain, risk, status, soft_wall
    ("fleet_get", "Fleet get", "fleet", "read", "live", False),
    ("fleet_search", "Fleet search", "fleet", "read", "live", False),
    ("vehicle_get", "Vehicle get", "fleet", "read", "live", False),
    ("vehicle_search", "Vehicle search", "fleet", "read", "live", False),
    ("driver_get", "Driver get", "fleet", "read", "live", False),
    ("driver_search", "Driver search", "fleet", "read", "live", False),
    ("trip_get", "Trip get", "fleet", "read", "live", False),
    ("trip_search", "Trip search", "fleet", "read", "live", False),
    ("geofence_get", "Geofence get", "fleet", "read", "live", False),
    ("geofence_search", "Geofence search", "fleet", "read", "live", False),
    ("alert_get", "Alert get", "ops", "read", "live", False),
    ("alert_search", "Alert search", "ops", "read", "live", False),
    ("maintenance_get", "Maintenance get", "ops", "read", "live", False),
    ("maintenance_search", "Maintenance search", "ops", "read", "live", False),
    ("position_summary", "Position summary", "telemetry", "read", "live", False),
    ("fuel_series_summary", "Fuel series summary", "telemetry", "read", "live", False),
    ("device_health", "Device health", "telemetry", "read", "live", False),
    ("sensor_health", "Sensor health", "telemetry", "read", "live", False),
    ("audit_get", "Audit get", "ops", "read", "live", False),
    ("fleet_brief", "Fleet brief", "ops", "read", "live", False),
    ("fuel_anomaly_explain", "Fuel anomaly explain", "fuel", "read", "live", True),
    ("theft_case_assess", "Theft case assess", "fuel", "propose", "live", True),
    ("route_deviation_explain", "Route deviation explain", "ops", "read", "live", False),
    ("idle_waste_summary", "Idle waste summary", "ops", "read", "live", False),
    ("driver_risk_summary", "Driver risk summary", "ops", "read", "live", True),
    ("maintenance_forecast", "Maintenance forecast", "ops", "read", "live", False),
    ("sensor_quality_assess", "Sensor quality assess", "telemetry", "read", "live", False),
    ("trip_report", "Trip report", "ops", "read", "live", False),
    ("ask_fleet", "Ask fleet", "ops", "read", "live", False),
    ("alert_rule_propose", "Alert rule propose", "ops", "propose", "live", True),
    ("maintenance_task_propose", "Maintenance task propose", "ops", "propose", "live", True),
    ("driver_message_draft", "Driver message draft", "ops", "outbound", "live", True),
    ("incident_case_propose", "Incident case propose", "ops", "propose", "live", True),
    ("geofence_change_propose", "Geofence change propose", "ops", "propose", "live", True),
    ("route_plan_propose", "Route plan propose", "ops", "propose", "live", True),
    ("fuel_reconciliation_propose", "Fuel reconciliation propose", "fuel", "propose", "live", True),
    ("notification_preview", "Notification preview", "ops", "propose", "live", True),
    ("notification_apply", "Notification apply", "ops", "outbound", "live", True),
    ("task_create", "Task create", "ops", "mutate", "live", True),
    ("case_create", "Case create", "ops", "mutate", "live", True),
    ("report_export", "Report export", "ops", "read", "live", True),
    ("vehicle_immobilise", "Vehicle immobilise", "control", "destructive", "disabled", True),
    ("fuel_cut", "Fuel cut", "control", "destructive", "disabled", True),
    ("tracker_config", "Tracker config", "control", "destructive", "disabled", True),
    ("firmware_update", "Firmware update", "control", "destructive", "disabled", True),
    ("geofence_apply", "Geofence apply", "control", "destructive", "disabled", True),
]


def build_fleetz_nodes() -> dict[str, CapabilityNode]:
    nodes: dict[str, CapabilityNode] = {}
    for key, title, domain, risk, status, soft_wall in _SPECS:
        nodes[key] = CapabilityNode(
            key=key,
            version="1.0.0",
            title=title,
            product="fleetz",
            domain=domain,
            risk=_RISK[risk],
            status=_STATUS[status],
            required_grants=(f"node:{key}",),
            entitlements=("fleetz",),
            soft_wall=soft_wall,
            sync=True,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            idempotent=key.endswith("_get") or key.endswith("_summary"),
            operator_guidance=(
                "Safety-critical vehicle control disabled; Fleetz product owns commands."
                if status == "disabled"
                else "Advisory Fleetz pack; product remains telemetry and control authority."
            ),
        )
    return nodes
