"""Honest capability nodes and routing for the Fleetz pack."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from tools.safety import command_capability_status

PACK_VERSION = "0.1.0"
CONTRACT_VERSION = "1.0"
PRODUCT_KEY = "fleetz"

READ_NODES = (
    "fleet_get",
    "fleet_search",
    "vehicle_get",
    "vehicle_search",
    "driver_get",
    "driver_search",
    "trip_get",
    "trip_search",
    "geofence_get",
    "geofence_search",
    "alert_get",
    "alert_search",
    "maintenance_get",
    "maintenance_search",
    "position_summary",
    "fuel_series_summary",
    "device_health",
    "sensor_health",
    "audit_get",
)

ANALYSIS_NODES = (
    "fleet_brief",
    "fuel_anomaly_explain",
    "theft_case_assess",
    "route_deviation_explain",
    "idle_waste_summary",
    "driver_risk_summary",
    "maintenance_forecast",
    "sensor_quality_assess",
    "trip_report",
    "ask_fleet",
)

PROPOSAL_NODES = (
    "alert_rule_propose",
    "maintenance_task_propose",
    "driver_message_draft",
    "incident_case_propose",
    "geofence_change_propose",
    "route_plan_propose",
    "fuel_reconciliation_propose",
)

ACTION_NODES = (
    "notification_preview",
    "notification_apply",
    "task_create",
    "case_create",
    "report_export",
)

# Advertised but disabled (safety)
DISABLED_COMMAND_NODES = (
    "vehicle_immobilise",
    "fuel_cut",
    "tracker_config",
    "firmware_update",
    "geofence_apply",
)

ALL_LIVE_NODES = (*READ_NODES, *ANALYSIS_NODES, *PROPOSAL_NODES, *ACTION_NODES)


def _node_classification(bare: str) -> str:
    if bare in READ_NODES:
        return "read"
    if bare in ANALYSIS_NODES:
        return "read"
    if bare in PROPOSAL_NODES:
        return "propose"
    if bare in ACTION_NODES:
        return "mutate" if bare.endswith("_apply") or bare.endswith("_create") else "propose"
    return "disabled"


def provider_health() -> dict[str, Any]:
    product_url = os.environ.get("FLEETZ_PRODUCT_API_URL", "").strip()
    fixture = os.environ.get("FLEETZ_USE_FIXTURES", "1").strip() not in {"0", "false", "False"}
    if product_url and not fixture:
        status = "live"
        primary = "fleetz-product-api"
    else:
        status = "stub"
        primary = "keprix-fleetz-fixture"
    return {
        "product_api_configured": bool(product_url),
        "fixtures_enabled": fixture or not product_url,
        "primary": primary,
        "status": status,
        "fallback_order": ["fleetz-product-api", "keprix-fleetz-fixture"],
        "hidden_fallback": False,
        "vehicle_commands": command_capability_status(),
    }


def canonical_tool_name(name: str) -> str:
    key = str(name or "").strip()
    if key.startswith("fleetz."):
        key = "fleetz_" + key[len("fleetz.") :]
    if key.startswith("fleetz_"):
        return key
    if key in ALL_LIVE_NODES or key in DISABLED_COMMAND_NODES:
        return f"fleetz_{key}"
    return key


def bare_tool_name(registry_name: str) -> str:
    name = str(registry_name or "")
    if name.startswith("fleetz_"):
        return name[len("fleetz_") :]
    if name.startswith("fleetz."):
        return name[len("fleetz.") :]
    return name


def capability_nodes(health: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    health = health or provider_health()
    nodes: list[dict[str, Any]] = []
    for bare in ALL_LIVE_NODES:
        classification = _node_classification(bare)
        status = health["status"]
        nodes.append(
            {
                "key": f"fleetz.{bare}",
                "version": PACK_VERSION,
                "title": bare.replace("_", " ").title(),
                "product": PRODUCT_KEY,
                "domain": "fleet_fuel_ops",
                "execution": "sync",
                "classification": classification,
                "high_risk": bare in {"theft_case_assess", "notification_apply", "case_create"},
                "required_grants": ["fleet_read" if classification == "read" else "fleet_ops"],
                "entitlements": ["fleetz_sidecar"],
                "approvals": ["operator_approval"] if classification in {"propose", "mutate"} else [],
                "accepted_context_slices": [
                    "fleet_scope",
                    "vehicle_ids",
                    "time_window",
                    "role",
                    "purpose",
                    "sensor_quality",
                ],
                "emitted_events": ["fleetz.analysis.completed", "fleetz.proposal.created"],
                "cost_class": "medium" if bare in ANALYSIS_NODES else "low",
                "timeout_seconds": 30,
                "concurrency_limit": 16,
                "retry_policy": "bounded_idempotent_only",
                "idempotency": "client_key_required_for_mutate",
                "cancellation": True,
                "data_classes": ["fleet_telemetry_summary", "operator_notes"],
                "retention": "product_retention_events",
                "redaction": "no_precise_routes_or_driver_pii_by_default",
                "residency": "GH",
                "model_requirements": health["fallback_order"],
                "deterministic_fallback": "keprix-fleetz-fixture",
                "health_dependencies": ["fleetz_product_or_fixture"],
                "status": status,
                "source": health["primary"],
                "operator_guidance": (
                    "Refuse definitive conclusions on stale/low-quality series."
                    if bare in ANALYSIS_NODES
                    else "Fleet-scoped projected reads only."
                    if classification == "read"
                    else "Proposal/apply requires product policy and approval evidence."
                ),
                "aliases": [bare, f"fleetz_{bare}", f"fleetz.{bare}"],
                "schemas_ref": f"schemas.json#{bare}",
            }
        )
    for bare in DISABLED_COMMAND_NODES:
        nodes.append(
            {
                "key": f"fleetz.{bare}",
                "version": PACK_VERSION,
                "title": bare.replace("_", " ").title(),
                "product": PRODUCT_KEY,
                "domain": "fleet_fuel_ops",
                "execution": "sync",
                "classification": "destructive",
                "high_risk": True,
                "required_grants": ["vehicle_control_none"],
                "entitlements": [],
                "approvals": ["two_person_product_owned"],
                "status": "disabled",
                "source": "disabled",
                "operator_guidance": "Safety-critical; not available on default sidecar.",
                "aliases": [bare, f"fleetz_{bare}"],
            }
        )
    return nodes


def capabilities_payload() -> dict[str, Any]:
    health = provider_health()
    return {
        "contract_version": CONTRACT_VERSION,
        "profile": "keprix",
        "pack_version": PACK_VERSION,
        "product_key": PRODUCT_KEY,
        "nodes": capability_nodes(health),
        "tools": [
            {
                "name": bare,
                "canonical": f"fleetz_{bare}",
                "aliases": [bare, f"fleetz_{bare}", f"fleetz.{bare}"],
                "status": health["status"],
                "source": health["primary"],
            }
            for bare in ALL_LIVE_NODES
        ]
        + [
            {
                "name": bare,
                "canonical": f"fleetz_{bare}",
                "status": "disabled",
                "source": "disabled",
            }
            for bare in DISABLED_COMMAND_NODES
        ],
        "provider_health": health,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "vehicle_commands_default": "disabled",
        "responsibility": {
            "product_owns": [
                "telemetry_truth",
                "primary_alerts",
                "vehicle_commands",
                "auth",
                "tenancy",
                "billing",
                "ui",
            ],
            "keprix_owns": [
                "fleet_intelligence_assist",
                "operator_playbooks",
                "proposal_drafts",
            ],
        },
    }


def pack_manifest() -> dict[str, Any]:
    return {
        "product_key": PRODUCT_KEY,
        "pack_id": PRODUCT_KEY,
        "version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "compatibility": {"fleetz_min": "0.1.0"},
        "policy": {
            "no_vehicle_commands": True,
            "no_traccar_command_api": True,
            "no_direct_sql": True,
            "data_minimisation": True,
            "advisory_default": True,
        },
        "migrations": [],
        "timezone_default": "Africa/Accra",
        "currency_default": "GHS",
        "northbound": [
            "/health",
            "/fleetz/capabilities",
            "/fleetz/tools/{name}",
            "/v1/products/fleetz/*",
        ],
        "southbound": [
            "/api/keprix/v1/health",
            "/api/keprix/v1/capabilities",
            "/api/keprix/v1/token/exchange",
            "/api/keprix/v1/context",
            "/api/keprix/v1/events/ack",
            "/api/keprix/v1/fleets/*",
            "/api/keprix/v1/vehicles/*",
            "/api/keprix/v1/actions/*",
        ],
    }
