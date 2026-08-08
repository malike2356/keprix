"""Deterministic Fleetz fleet/fuel calculators.

LLM handlers must call these for numbers. Never recalculate from sampled prose.
"""

from __future__ import annotations

import math
from typing import Any

FORMULA_VERSION = "fleetz-calc@1.0.0"
EARTH_RADIUS_M = 6_371_000.0

# Ghana defaults (display only; sensors keep original units)
DEFAULT_TIMEZONE = "Africa/Accra"
DEFAULT_CURRENCY = "GHS"
DEFAULT_DISTANCE_UNIT = "km"
DEFAULT_FUEL_UNIT = "L"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def path_distance_m(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(points)):
        lat1, lon1 = points[i - 1]
        lat2, lon2 = points[i]
        total += haversine_m(lat1, lon1, lat2, lon2)
    return total


def fuel_delta_l(start_l: float, end_l: float) -> float:
    """Signed fuel change (negative = consume/drain)."""
    return float(end_l) - float(start_l)


def fuel_rate_l_per_100km(fuel_used_l: float, distance_m: float) -> float | None:
    if distance_m <= 0 or fuel_used_l < 0:
        return None
    km = distance_m / 1000.0
    if km <= 0:
        return None
    return (fuel_used_l / km) * 100.0


def idle_duration_s(segments: list[dict[str, Any]]) -> float:
    """Sum idle seconds from segments with speed_kph below threshold."""
    total = 0.0
    for seg in segments:
        if float(seg.get("speed_kph") or 0) < float(seg.get("idle_threshold_kph") or 3.0):
            total += float(seg.get("duration_s") or 0)
    return total


def point_in_geofence(lat: float, lon: float, polygon: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon. Product PostGIS remains authoritative for apply."""
    if len(polygon) < 3:
        return False
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i][0], polygon[i][1]
        yj, xj = polygon[j][0], polygon[j][1]
        if ((xi > lon) != (xj > lon)) and (lat < (yj - yi) * (lon - xi) / ((xj - xi) or 1e-12) + yi):
            inside = not inside
        j = i
    return inside


def freshness_age_s(*, event_time_epoch_s: float, now_epoch_s: float) -> float:
    return max(0.0, float(now_epoch_s) - float(event_time_epoch_s))


def is_stale(*, age_s: float, max_age_s: float) -> bool:
    return float(age_s) > float(max_age_s)


def sensor_quality_score(
    *,
    sample_count: int,
    gap_ratio: float,
    calibration_age_days: float,
    spoof_flags: int = 0,
) -> dict[str, Any]:
    """0..1 quality; below 0.5 is non-actionable for definitive claims."""
    if sample_count <= 0:
        return {
            "score": 0.0,
            "label": "insufficient",
            "actionable": False,
            "formula_version": FORMULA_VERSION,
        }
    score = 1.0
    score -= min(0.5, max(0.0, gap_ratio) * 0.8)
    if calibration_age_days > 180:
        score -= 0.25
    elif calibration_age_days > 90:
        score -= 0.1
    score -= min(0.4, spoof_flags * 0.2)
    score = max(0.0, min(1.0, score))
    actionable = score >= 0.5 and sample_count >= 3 and spoof_flags == 0
    label = "good" if score >= 0.8 else "fair" if score >= 0.5 else "poor"
    return {
        "score": round(score, 4),
        "label": label,
        "actionable": actionable,
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
    }


def maintenance_due(
    *,
    odometer_km: float,
    engine_hours: float,
    last_service_odometer_km: float,
    last_service_engine_hours: float,
    interval_km: float,
    interval_hours: float,
) -> dict[str, Any]:
    km_remaining = interval_km - (odometer_km - last_service_odometer_km)
    hours_remaining = interval_hours - (engine_hours - last_service_engine_hours)
    overdue = km_remaining <= 0 or hours_remaining <= 0
    return {
        "km_remaining": round(km_remaining, 2),
        "hours_remaining": round(hours_remaining, 2),
        "overdue": overdue,
        "due_window": "overdue" if overdue else "upcoming" if min(km_remaining, hours_remaining) < interval_km * 0.1 else "ok",
        "formula_version": FORMULA_VERSION,
        "value_kind": "calculated",
    }


def coalesce_event_batch(events: list[dict[str, Any]], *, window_s: float = 60.0) -> list[dict[str, Any]]:
    """Batch events by fleet/vehicle within a time window for storm protection."""
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ev in events:
        key = (str(ev.get("fleet_id") or ""), str(ev.get("vehicle_id") or ""))
        buckets.setdefault(key, []).append(ev)
    out: list[dict[str, Any]] = []
    for (fleet_id, vehicle_id), group in buckets.items():
        group_sorted = sorted(group, key=lambda e: float(e.get("occurred_epoch_s") or 0))
        batch: list[dict[str, Any]] = []
        batch_start = None
        for ev in group_sorted:
            t = float(ev.get("occurred_epoch_s") or 0)
            if batch_start is None:
                batch_start = t
                batch = [ev]
                continue
            if t - batch_start <= window_s:
                batch.append(ev)
            else:
                out.append(
                    {
                        "fleet_id": fleet_id,
                        "vehicle_id": vehicle_id,
                        "count": len(batch),
                        "first_epoch_s": batch_start,
                        "last_epoch_s": float(batch[-1].get("occurred_epoch_s") or batch_start),
                        "priority": max(int(e.get("priority") or 0) for e in batch),
                        "event_ids": [e.get("id") for e in batch],
                        "types": sorted({str(e.get("type") or "") for e in batch}),
                    }
                )
                batch_start = t
                batch = [ev]
        if batch and batch_start is not None:
            out.append(
                {
                    "fleet_id": fleet_id,
                    "vehicle_id": vehicle_id,
                    "count": len(batch),
                    "first_epoch_s": batch_start,
                    "last_epoch_s": float(batch[-1].get("occurred_epoch_s") or batch_start),
                    "priority": max(int(e.get("priority") or 0) for e in batch),
                    "event_ids": [e.get("id") for e in batch],
                    "types": sorted({str(e.get("type") or "") for e in batch}),
                }
            )
    return out


def result_envelope(
    *,
    fleet_id: str,
    vehicle_id: str | None = None,
    event_ids: list[str] | None = None,
    source_window: dict[str, Any] | None = None,
    freshness: dict[str, Any] | None = None,
    sensor_quality: dict[str, Any] | None = None,
    units: dict[str, str] | None = None,
    confidence: float = 0.0,
    value_kind: str = "observed",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "event_ids": event_ids or [],
        "source_window": source_window or {},
        "freshness": freshness or {},
        "sensor_quality": sensor_quality or {},
        "units": units
        or {
            "distance": DEFAULT_DISTANCE_UNIT,
            "fuel": DEFAULT_FUEL_UNIT,
            "timezone": DEFAULT_TIMEZONE,
            "currency": DEFAULT_CURRENCY,
        },
        "confidence": confidence,
        "value_kind": value_kind,  # observed | derived | inferred
        "formula_version": FORMULA_VERSION,
        "result": payload or {},
    }
