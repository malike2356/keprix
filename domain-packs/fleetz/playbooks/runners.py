"""Operator playbook runners for Fleetz (alert, fuel, maintenance, briefing)."""

from __future__ import annotations

import json
from typing import Any

from tools import handlers
from tools.safety import emergency_route_to_human, strip_accusation_language, treat_as_operator_text


def _parse(raw: str) -> dict[str, Any]:
    return json.loads(raw)


def playbook_fuel_investigation(args: dict[str, Any]) -> dict[str, Any]:
    """Correlate quality, drain pattern, and propose case without accusation."""
    explain = _parse(handlers.fleetz_fuel_anomaly_explain_handler(args))
    if explain.get("status") == "refused" or explain.get("reason") in {
        "stale_telemetry",
        "insufficient_series",
        "low_sensor_quality",
    }:
        return {
            "playbook": "fuel_investigation",
            "stopped": True,
            "stop_condition": explain.get("reason") or "refused",
            "result": explain,
            "human_takeover": True,
        }
    case_draft = _parse(
        handlers.fleetz_incident_case_propose_handler(
            {
                **args,
                "title": "Fuel anomaly investigation",
                "hypothesis": strip_accusation_language(
                    ((explain.get("result") or {}).get("hypothesis") if isinstance(explain.get("result"), dict) else None)
                    or "Possible fuel anomaly; review evidence."
                ),
                "event_ids": args.get("event_ids") or ["alert-fuel-01"],
            }
        )
    )
    return {
        "playbook": "fuel_investigation",
        "evidence": explain,
        "case_proposal": case_draft,
        "accusation": False,
        "human_takeover": False,
        "audit": {"steps": ["fuel_anomaly_explain", "incident_case_propose"]},
        "costs": {"model_calls": 0, "deterministic": True},
        "retries": {"max": 1, "idempotent_apply": True},
    }


def playbook_alert_triage(args: dict[str, Any]) -> dict[str, Any]:
    alerts_raw = _parse(handlers.fleetz_alert_search_handler(args))
    alerts = alerts_raw.get("alerts") or []
    # Group duplicates
    groups: dict[str, list[dict[str, Any]]] = {}
    for alert in alerts:
        key = str(alert.get("duplicate_of") or alert.get("id"))
        groups.setdefault(key, []).append(alert)
    primary_ids = list(groups.keys())
    proposals = []
    for aid in primary_ids[:5]:
        proposals.append(
            _parse(
                handlers.fleetz_incident_case_propose_handler(
                    {
                        **args,
                        "title": f"Triage {aid}",
                        "event_ids": [a["id"] for a in groups[aid]],
                        "hypothesis": "Grouped alert triage; freshness and severity to be confirmed in product.",
                    }
                )
            )
        )
    # Idempotent notification: same key cannot duplicate outbound
    notif = None
    if args.get("notify") and args.get("approval_evidence"):
        notif = _parse(
            handlers.fleetz_notification_apply_handler(
                {
                    **args,
                    "body": "Alert triage summary ready for review.",
                    "idempotency_key": args.get("idempotency_key") or f"triage-{args.get('fleet_id')}",
                }
            )
        )
        # second apply must mark duplicate
        notif2 = _parse(
            handlers.fleetz_notification_apply_handler(
                {
                    **args,
                    "body": "Alert triage summary ready for review.",
                    "idempotency_key": args.get("idempotency_key") or f"triage-{args.get('fleet_id')}",
                }
            )
        )
        notif = {"first": notif, "second": notif2, "duplicate_prevented": bool(notif2.get("duplicate"))}
    return {
        "playbook": "alert_triage",
        "groups": {k: [a["id"] for a in v] for k, v in groups.items()},
        "proposals": proposals,
        "notification": notif,
        "stop_conditions": ["stale_primary_alert", "kill_switch", "missing_approval"],
        "human_takeover": True,
        "audit": {"steps": ["alert_search", "group_duplicates", "case_propose", "optional_notify"]},
    }


def playbook_maintenance_workflow(args: dict[str, Any]) -> dict[str, Any]:
    forecast = _parse(handlers.fleetz_maintenance_forecast_handler(args))
    propose = _parse(handlers.fleetz_maintenance_task_propose_handler(args))
    return {
        "playbook": "maintenance_workflow",
        "forecast": forecast,
        "task_proposal": propose,
        "deterministic_trace": True,
        "human_takeover": False,
        "audit": {"steps": ["maintenance_forecast", "maintenance_task_propose"]},
    }


def playbook_daily_fleet_briefing(args: dict[str, Any]) -> dict[str, Any]:
    brief = _parse(handlers.fleetz_fleet_brief_handler(args))
    return {
        "playbook": "daily_fleet_briefing",
        "brief": brief,
        "clickable_record_ids": (brief.get("result") or brief).get("record_ids")
        if isinstance(brief.get("result"), dict)
        else brief.get("record_ids"),
        "human_takeover": False,
        "audit": {"steps": ["fleet_brief"]},
    }


def playbook_driver_message(args: dict[str, Any]) -> dict[str, Any]:
    note = treat_as_operator_text(str(args.get("message") or ""))
    if note["command_request_detected"] or args.get("emergency"):
        return {
            "playbook": "driver_message",
            "routed": emergency_route_to_human(note["text"]),
            "auto_send": False,
        }
    draft = _parse(handlers.fleetz_driver_message_draft_handler(args))
    return {
        "playbook": "driver_message",
        "draft": draft,
        "approval_required": True,
        "location_detail": "minimum",
        "group_chat_driver_data": False,
    }


def playbook_route_geofence_optimisation(args: dict[str, Any]) -> dict[str, Any]:
    geo = _parse(handlers.fleetz_geofence_change_propose_handler(args))
    route = _parse(handlers.fleetz_route_plan_propose_handler(args))
    return {
        "playbook": "route_geofence_optimisation",
        "geofence_proposal": geo,
        "route_proposal": route,
        "apply_allowed": False,
        "product_must_validate_geometry": True,
    }


PLAYBOOKS = {
    "fuel_investigation": playbook_fuel_investigation,
    "alert_triage": playbook_alert_triage,
    "maintenance_workflow": playbook_maintenance_workflow,
    "daily_fleet_briefing": playbook_daily_fleet_briefing,
    "driver_message": playbook_driver_message,
    "route_geofence_optimisation": playbook_route_geofence_optimisation,
}


def run_playbook(name: str, args: dict[str, Any]) -> dict[str, Any]:
    fn = PLAYBOOKS.get(name)
    if not fn:
        return {"status": "error", "error": f"unknown_playbook:{name}"}
    return fn(args)
