"""Fleetz sidecar tool handlers (fixture-backed, deterministic calculations)."""

from __future__ import annotations

import json
import time
from typing import Any

from calculators.formulas import (
    coalesce_event_batch,
    fuel_delta_l,
    fuel_rate_l_per_100km,
    freshness_age_s,
    idle_duration_s,
    is_stale,
    maintenance_due,
    path_distance_m,
    result_envelope,
    sensor_quality_score,
)
from connector.product_client import FleetzProductClient
from tools.contract import DISABLED_COMMAND_NODES, provider_health
from tools.safety import (
    assert_no_vehicle_command,
    emergency_route_to_human,
    minimise_location,
    refuse_if_stale,
    strip_accusation_language,
    treat_as_operator_text,
)

_client: FleetzProductClient | None = None
_idempotency: dict[str, dict[str, Any]] = {}


def _get_client() -> FleetzProductClient:
    global _client
    if _client is None:
        _client = FleetzProductClient()
    return _client


def _ok(payload: dict[str, Any]) -> str:
    health = provider_health()
    body = {
        "status": "ok",
        "source": health["primary"],
        "provider_status": health["status"],
        **payload,
    }
    return json.dumps(body)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"status": "error", "error": message, **extra})


def _scope(args: dict[str, Any]) -> tuple[str, str | None]:
    fleet_id = str(args.get("fleet_id") or args.get("tenant_id") or "").strip()
    vehicle_id = args.get("vehicle_id")
    vehicle_id = str(vehicle_id).strip() if vehicle_id else None
    return fleet_id, vehicle_id


def _require_fleet(args: dict[str, Any]) -> str | None:
    fleet_id, _ = _scope(args)
    if not fleet_id:
        return _err("fleet_id_required")
    return None


def _quality_from_args(args: dict[str, Any]) -> dict[str, Any]:
    return sensor_quality_score(
        sample_count=int(args.get("sample_count") or args.get("points") and len(args["points"]) or 0),
        gap_ratio=float(args.get("gap_ratio") or 0.0),
        calibration_age_days=float(args.get("calibration_age_days") or 30.0),
        spoof_flags=int(args.get("spoof_flags") or 0),
    )


def _freshness_from_args(args: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    now = now or time.time()
    event_epoch = args.get("event_time_epoch_s")
    if event_epoch is None and args.get("occurred_at_epoch_s") is not None:
        event_epoch = args["occurred_at_epoch_s"]
    if event_epoch is None:
        # Prefer product summary freshness when present
        event_epoch = args.get("last_point_epoch_s")
    if event_epoch is None:
        return {"age_s": None, "stale": False, "unknown": True}
    age = freshness_age_s(event_time_epoch_s=float(event_epoch), now_epoch_s=now)
    max_age = float(args.get("max_age_s") or 900.0)
    return {"age_s": age, "stale": is_stale(age_s=age, max_age_s=max_age), "max_age_s": max_age, "unknown": False}


# --- Reads ---


def fleetz_fleet_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    data = _get_client().get_fleet(fleet_id)
    if not data:
        return _err("fleet_not_found_or_denied", fleet_id=fleet_id)
    return _ok({"fleet": data})


def fleetz_fleet_search_handler(args: dict[str, Any]) -> str:
    actor_fleet = str(args.get("fleet_id") or args.get("actor_fleet_id") or "").strip()
    rows = _get_client().search_fleets(query=str(args.get("query") or ""), actor_fleet_id=actor_fleet)
    return _ok({"fleets": rows, "count": len(rows)})


def fleetz_vehicle_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    if not vehicle_id:
        return _err("vehicle_id_required")
    data = _get_client().get_vehicle(fleet_id, vehicle_id)
    if not data:
        return _err("vehicle_not_found_or_denied")
    return _ok({"vehicle": data})


def fleetz_vehicle_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    rows = _get_client().search_vehicles(fleet_id, query=str(args.get("query") or ""))
    return _ok({"vehicles": rows, "count": len(rows)})


def fleetz_driver_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    role = str(args.get("role") or "operator")
    purpose = str(args.get("purpose") or "ops")
    driver_id = str(args.get("driver_id") or "")
    data = _get_client().get_driver(fleet_id, driver_id, role=role, purpose=purpose)
    if not data:
        return _err("driver_not_found_or_denied")
    return _ok({"driver": data})


def fleetz_driver_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    rows = _get_client().search_drivers(fleet_id, query=str(args.get("query") or ""))
    return _ok({"drivers": rows, "count": len(rows)})


def fleetz_trip_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    trip = _get_client().get_trip(fleet_id, str(args.get("trip_id") or ""))
    if not trip:
        return _err("trip_not_found_or_denied")
    return _ok({"trip": trip})


def fleetz_trip_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    rows = _get_client().search_trips(
        fleet_id,
        vehicle_id=vehicle_id,
        start_epoch_s=args.get("start_epoch_s"),
        end_epoch_s=args.get("end_epoch_s"),
        cursor=args.get("cursor"),
        limit=int(args.get("limit") or 50),
    )
    return _ok(rows)


def fleetz_geofence_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    row = _get_client().get_geofence(fleet_id, str(args.get("geofence_id") or ""))
    if not row:
        return _err("geofence_not_found_or_denied")
    return _ok({"geofence": row})


def fleetz_geofence_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    rows = _get_client().search_geofences(fleet_id)
    return _ok({"geofences": rows, "count": len(rows)})


def fleetz_alert_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    row = _get_client().get_alert(fleet_id, str(args.get("alert_id") or ""))
    if not row:
        return _err("alert_not_found_or_denied")
    return _ok({"alert": row})


def fleetz_alert_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    rows = _get_client().search_alerts(fleet_id, vehicle_id=vehicle_id, status=args.get("status"))
    return _ok({"alerts": rows, "count": len(rows)})


def fleetz_maintenance_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    row = _get_client().get_maintenance(fleet_id, str(args.get("maintenance_id") or ""))
    if not row:
        return _err("maintenance_not_found_or_denied")
    return _ok({"maintenance": row})


def fleetz_maintenance_search_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    rows = _get_client().search_maintenance(fleet_id, vehicle_id=vehicle_id)
    return _ok({"maintenance": rows, "count": len(rows)})


def fleetz_position_summary_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    if not vehicle_id:
        return _err("vehicle_id_required")
    summary = _get_client().position_summary(
        fleet_id,
        vehicle_id,
        start_epoch_s=float(args.get("start_epoch_s") or time.time() - 3600),
        end_epoch_s=float(args.get("end_epoch_s") or time.time()),
        resolution=str(args.get("resolution") or "5m"),
        max_points=int(args.get("max_points") or 200),
    )
    return _ok({"position_summary": summary})


def fleetz_fuel_series_summary_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    if not vehicle_id:
        return _err("vehicle_id_required")
    summary = _get_client().fuel_series_summary(
        fleet_id,
        vehicle_id,
        start_epoch_s=float(args.get("start_epoch_s") or time.time() - 86400),
        end_epoch_s=float(args.get("end_epoch_s") or time.time()),
        resolution=str(args.get("resolution") or "15m"),
        max_points=int(args.get("max_points") or 200),
    )
    return _ok({"fuel_series_summary": summary})


def fleetz_device_health_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    row = _get_client().device_health(fleet_id, vehicle_id)
    return _ok({"device_health": row})


def fleetz_sensor_health_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    row = _get_client().sensor_health(fleet_id, vehicle_id)
    return _ok({"sensor_health": row})


def fleetz_audit_get_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    rows = _get_client().audit_entries(fleet_id, limit=int(args.get("limit") or 50))
    return _ok({"audit": rows, "count": len(rows)})


# --- Analysis ---


def fleetz_fleet_brief_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    brief = _get_client().fleet_brief(fleet_id)
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            confidence=0.85,
            value_kind="derived",
            payload={
                "offline_vehicles": brief.get("offline_vehicles", []),
                "active_alerts": brief.get("active_alerts", []),
                "fuel_summary": brief.get("fuel_summary", {}),
                "utilisation": brief.get("utilisation", {}),
                "maintenance": brief.get("maintenance", []),
                "overdue_cases": brief.get("overdue_cases", []),
                "data_quality_gaps": brief.get("data_quality_gaps", []),
                "record_ids": brief.get("record_ids", {}),
            },
        )
    )


def fleetz_fuel_anomaly_explain_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    if not vehicle_id:
        return _err("vehicle_id_required")
    quality = _quality_from_args(args) if args.get("sample_count") is not None else _get_client().sensor_quality(fleet_id, vehicle_id)
    fresh = _freshness_from_args(args)
    refusal = refuse_if_stale(
        age_s=fresh.get("age_s"),
        max_age_s=float(args.get("max_age_s") or 3600),
        sample_count=int(args.get("sample_count") or quality.get("sample_count") or 0),
        quality_actionable=bool(quality.get("actionable", True)),
    )
    if refusal:
        return _ok({**refusal, "fleet_id": fleet_id, "vehicle_id": vehicle_id})

    start_l = float(args.get("start_fuel_l") or args.get("fuel_start_l") or 0)
    end_l = float(args.get("end_fuel_l") or args.get("fuel_end_l") or 0)
    if not start_l and not end_l:
        series = _get_client().fuel_series_summary(
            fleet_id,
            vehicle_id,
            start_epoch_s=float(args.get("start_epoch_s") or time.time() - 86400),
            end_epoch_s=float(args.get("end_epoch_s") or time.time()),
        )
        start_l = float(series.get("start_fuel_l") or 0)
        end_l = float(series.get("end_fuel_l") or 0)
        args.setdefault("sample_count", series.get("sample_count", 0))

    delta = fuel_delta_l(start_l, end_l)
    distance_m = float(args.get("distance_m") or 0)
    rate = fuel_rate_l_per_100km(abs(min(0.0, delta)), distance_m) if delta < 0 else None
    evidence = {
        "fuel_delta_l": round(delta, 3),
        "start_fuel_l": start_l,
        "end_fuel_l": end_l,
        "distance_m": distance_m,
        "rate_l_per_100km": rate,
        "sensor_quality": quality,
        "freshness": fresh,
        "refuel_or_drain_pattern": "drain" if delta < -5 else "refuel" if delta > 5 else "stable",
        "route_stop_ignition": args.get("context_flags") or {},
    }
    hypothesis = strip_accusation_language(
        str(args.get("hypothesis") or "Possible fuel anomaly; investigate with product evidence.")
    )
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            event_ids=list(args.get("event_ids") or []),
            freshness=fresh,
            sensor_quality=quality,
            confidence=0.7 if quality.get("actionable") else 0.3,
            value_kind="inferred",
            payload={
                "evidence": evidence,
                "hypothesis": hypothesis,
                "accusation": False,
                "next_evidence": [
                    "confirm_sensor_calibration",
                    "review_stop_locations_summary",
                    "compare_baseline_consumption",
                ],
            },
        )
    )


def fleetz_theft_case_assess_handler(args: dict[str, Any]) -> str:
    # Alias framing around fuel anomaly with explicit no-accusation contract
    base = json.loads(fleetz_fuel_anomaly_explain_handler(args))
    if base.get("status") == "error":
        return json.dumps(base)
    result = base.get("result") or base
    payload = result.get("result") if isinstance(result, dict) and "result" in result else result
    if isinstance(payload, dict):
        payload["case_framing"] = "hypothesis_only"
        payload["accusation"] = False
        payload["language"] = "Do not accuse drivers or staff; present evidence for human review."
    return json.dumps(base)


def fleetz_route_deviation_explain_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    role = str(args.get("role") or "operator")
    purpose = str(args.get("purpose") or "route_deviation_explain")
    points = args.get("points") or []
    tuples = [(float(p["lat"]), float(p["lon"])) for p in points if "lat" in p and "lon" in p]
    distance_m = path_distance_m(tuples) if tuples else float(args.get("distance_m") or 0)
    loc = minimise_location(role=role, purpose=purpose, precise_points=points, allow_precise=bool(args.get("allow_precise")))
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            confidence=0.75,
            value_kind="derived",
            payload={
                "planned_vs_actual_distance_m": distance_m,
                "deviation_m": float(args.get("deviation_m") or 0),
                "location": loc,
                "explanation": "Route deviation calculated from projected points; product PostGIS remains authoritative.",
            },
        )
    )


def fleetz_idle_waste_summary_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    segments = args.get("segments") or _get_client().idle_segments(fleet_id, vehicle_id)
    idle_s = idle_duration_s(segments)
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            confidence=0.9,
            value_kind="calculated",
            payload={"idle_duration_s": idle_s, "segment_count": len(segments)},
        )
    )


def fleetz_driver_risk_summary_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    role = str(args.get("role") or "fleet_manager")
    purpose = str(args.get("purpose") or "driver_risk_summary")
    if role not in {"fleet_manager", "owner", "dispatcher"}:
        return _err("driver_risk_denied_for_role", role=role)
    summary = _get_client().driver_risk_summary(fleet_id, str(args.get("driver_id") or ""))
    # Never return off-duty tracking
    summary.pop("off_duty_tracks", None)
    summary["purpose"] = purpose
    summary["minimised"] = True
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            confidence=0.65,
            value_kind="inferred",
            payload=summary,
        )
    )


def fleetz_maintenance_forecast_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    if not vehicle_id:
        return _err("vehicle_id_required")
    vehicle = _get_client().get_vehicle(fleet_id, vehicle_id) or {}
    due = maintenance_due(
        odometer_km=float(args.get("odometer_km") or vehicle.get("odometer_km") or 0),
        engine_hours=float(args.get("engine_hours") or vehicle.get("engine_hours") or 0),
        last_service_odometer_km=float(args.get("last_service_odometer_km") or vehicle.get("last_service_odometer_km") or 0),
        last_service_engine_hours=float(args.get("last_service_engine_hours") or vehicle.get("last_service_engine_hours") or 0),
        interval_km=float(args.get("interval_km") or 10000),
        interval_hours=float(args.get("interval_hours") or 500),
    )
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            confidence=0.95,
            value_kind="calculated",
            payload={"forecast": due, "evidence_ids": vehicle.get("ids") or {}},
        )
    )


def fleetz_sensor_quality_assess_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    quality = _quality_from_args(args) if args.get("sample_count") is not None else _get_client().sensor_quality(fleet_id, vehicle_id)
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id,
            sensor_quality=quality,
            confidence=1.0,
            value_kind="calculated",
            payload=quality,
        )
    )


def fleetz_trip_report_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    trip_id = str(args.get("trip_id") or "")
    trip = _get_client().get_trip(fleet_id, trip_id) if trip_id else None
    if not trip:
        return _err("trip_not_found_or_denied")
    loc = minimise_location(
        role=str(args.get("role") or "fleet_manager"),
        purpose="trip_report",
        precise_points=trip.get("points"),
        allow_precise=bool(args.get("allow_precise")),
    )
    return _ok(
        result_envelope(
            fleet_id=fleet_id,
            vehicle_id=vehicle_id or trip.get("vehicle_id"),
            event_ids=[trip_id],
            confidence=0.9,
            value_kind="derived",
            payload={"trip": {k: v for k, v in trip.items() if k != "points"}, "location": loc},
        )
    )


def fleetz_ask_fleet_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    question = treat_as_operator_text(str(args.get("question") or ""))
    if question["command_request_detected"]:
        return _ok(emergency_route_to_human(question["text"]))
    brief = _get_client().fleet_brief(fleet_id)
    answer = (
        f"Fleet {fleet_id}: {len(brief.get('active_alerts') or [])} active alerts, "
        f"{len(brief.get('offline_vehicles') or [])} offline vehicles. "
        "Advisory only; product remains source of truth."
    )
    return _ok(
        {
            "fleet_id": fleet_id,
            "question": question,
            "answer": answer,
            "record_ids": brief.get("record_ids", {}),
            "value_kind": "inferred",
            "confidence": 0.55,
        }
    )


# --- Proposals ---


def _proposal(kind: str, args: dict[str, Any], draft: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    return _ok(
        {
            "proposal_only": True,
            "kind": kind,
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "draft": draft,
            "requires_product_validation": True,
            "apply_allowed": kind not in {"geofence_change", "route_plan"},
        }
    )


def fleetz_alert_rule_propose_handler(args: dict[str, Any]) -> str:
    return _proposal(
        "alert_rule",
        args,
        {
            "name": args.get("name") or "proposed_alert_rule",
            "condition": args.get("condition") or {},
            "severity": args.get("severity") or "medium",
        },
    )


def fleetz_maintenance_task_propose_handler(args: dict[str, Any]) -> str:
    forecast = json.loads(fleetz_maintenance_forecast_handler(args))
    draft = {
        "title": args.get("title") or "Scheduled maintenance",
        "parts": args.get("parts") or ["filter", "oil"],
        "due_window": (forecast.get("result") or {}).get("forecast") or forecast.get("forecast"),
        "evidence": forecast,
    }
    return _proposal("maintenance_task", args, draft)


def fleetz_driver_message_draft_handler(args: dict[str, Any]) -> str:
    note = treat_as_operator_text(str(args.get("message") or args.get("draft") or ""))
    if note["command_request_detected"]:
        return _ok(emergency_route_to_human(note["text"]))
    language = str(args.get("language") or "en")
    channel = str(args.get("channel") or "push")
    text = strip_accusation_language(note["text"]) or "Please drive safely and follow assigned route."
    return _proposal(
        "driver_message",
        args,
        {
            "text": text,
            "language": language,
            "channel": channel,
            "location_detail": "minimum",
            "neutral_safety_language": True,
            "approval_required": True,
        },
    )


def fleetz_incident_case_propose_handler(args: dict[str, Any]) -> str:
    return _proposal(
        "incident_case",
        args,
        {
            "title": args.get("title") or "Incident case",
            "evidence_ids": args.get("event_ids") or [],
            "hypothesis": strip_accusation_language(str(args.get("hypothesis") or "")),
            "accusation": False,
        },
    )


def fleetz_geofence_change_propose_handler(args: dict[str, Any]) -> str:
    # Preview only; apply disabled
    out = json.loads(
        _proposal(
            "geofence_change",
            args,
            {
                "geofence_id": args.get("geofence_id"),
                "geometry": args.get("geometry") or {},
                "preview_only": True,
            },
        )
    )
    out["apply_allowed"] = False
    out["note"] = "Geofence changes remain product-validated simulation/preview only."
    return json.dumps(out)


def fleetz_route_plan_propose_handler(args: dict[str, Any]) -> str:
    out = json.loads(
        _proposal(
            "route_plan",
            args,
            {"waypoints": args.get("waypoints") or [], "simulation": True},
        )
    )
    out["apply_allowed"] = False
    return json.dumps(out)


def fleetz_fuel_reconciliation_propose_handler(args: dict[str, Any]) -> str:
    explain = json.loads(fleetz_fuel_anomaly_explain_handler(args))
    return _proposal(
        "fuel_reconciliation",
        args,
        {"based_on": explain, "adjustments": args.get("adjustments") or []},
    )


# --- Safe actions ---


def _idempotent(key: str | None, build) -> str:
    if key and key in _idempotency:
        prior = _idempotency[key]
        return _ok({**prior, "duplicate": True})
    result = build()
    if key:
        _idempotency[key] = {k: v for k, v in result.items() if k != "status"}
    return _ok({**result, "duplicate": False})


def fleetz_notification_preview_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, vehicle_id = _scope(args)
    return _ok(
        {
            "preview": True,
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "channel": args.get("channel") or "push",
            "body": strip_accusation_language(str(args.get("body") or "")),
            "approval_required": True,
        }
    )


def fleetz_notification_apply_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    if not args.get("approval_evidence"):
        return _err("approval_evidence_required")
    fleet_id, vehicle_id = _scope(args)
    key = args.get("idempotency_key")

    def build() -> dict[str, Any]:
        applied = _get_client().apply_notification(
            fleet_id,
            vehicle_id=vehicle_id,
            channel=str(args.get("channel") or "push"),
            body=strip_accusation_language(str(args.get("body") or "")),
            approval_evidence=args.get("approval_evidence"),
            object_version=args.get("object_version"),
            idempotency_key=key,
        )
        return {"applied": True, "notification": applied}

    return _idempotent(str(key) if key else None, build)


def fleetz_task_create_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    if not args.get("approval_evidence"):
        return _err("approval_evidence_required")
    fleet_id, vehicle_id = _scope(args)
    key = args.get("idempotency_key")

    def build() -> dict[str, Any]:
        task = _get_client().create_task(
            fleet_id,
            vehicle_id=vehicle_id,
            title=str(args.get("title") or "Task"),
            payload=args.get("payload") or {},
            approval_evidence=args.get("approval_evidence"),
            idempotency_key=key,
        )
        return {"task": task}

    return _idempotent(str(key) if key else None, build)


def fleetz_case_create_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    if not args.get("approval_evidence"):
        return _err("approval_evidence_required")
    fleet_id, vehicle_id = _scope(args)
    key = args.get("idempotency_key")

    def build() -> dict[str, Any]:
        case = _get_client().create_case(
            fleet_id,
            vehicle_id=vehicle_id,
            title=str(args.get("title") or "Case"),
            evidence_ids=list(args.get("event_ids") or []),
            hypothesis=strip_accusation_language(str(args.get("hypothesis") or "")),
            approval_evidence=args.get("approval_evidence"),
            idempotency_key=key,
        )
        return {"case": case}

    return _idempotent(str(key) if key else None, build)


def fleetz_report_export_handler(args: dict[str, Any]) -> str:
    if err := _require_fleet(args):
        return err
    fleet_id, _ = _scope(args)
    if bool(args.get("precise_routes")) and str(args.get("role") or "") not in {"owner", "fleet_manager"}:
        return _err("precise_route_export_denied")
    report = _get_client().export_report(
        fleet_id,
        report_type=str(args.get("report_type") or "fleet_daily"),
        precise_routes=False,
    )
    return _ok({"report": report, "precise_routes": False})


def fleetz_disabled_command_handler(args: dict[str, Any]) -> str:
    capability = str(args.get("capability") or args.get("_capability") or "vehicle_command")
    denied = assert_no_vehicle_command(capability)
    return json.dumps(denied or {"status": "error", "error": "vehicle_command_disabled"})


def fleetz_event_coalesce_handler(args: dict[str, Any]) -> str:
    events = args.get("events") or []
    batches = coalesce_event_batch(events, window_s=float(args.get("window_s") or 60))
    return _ok({"batches": batches, "input_count": len(events), "batch_count": len(batches)})


# Map disabled command names to deny handler for registry
DISABLED_HANDLERS = {f"fleetz_{name}": fleetz_disabled_command_handler for name in DISABLED_COMMAND_NODES}
