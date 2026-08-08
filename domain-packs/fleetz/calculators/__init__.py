"""Fleetz calculators package."""

from calculators.formulas import (
    FORMULA_VERSION,
    coalesce_event_batch,
    fuel_delta_l,
    fuel_rate_l_per_100km,
    freshness_age_s,
    haversine_m,
    idle_duration_s,
    is_stale,
    maintenance_due,
    path_distance_m,
    point_in_geofence,
    result_envelope,
    sensor_quality_score,
)

__all__ = [
    "FORMULA_VERSION",
    "coalesce_event_batch",
    "fuel_delta_l",
    "fuel_rate_l_per_100km",
    "freshness_age_s",
    "haversine_m",
    "idle_duration_s",
    "is_stale",
    "maintenance_due",
    "path_distance_m",
    "point_in_geofence",
    "result_envelope",
    "sensor_quality_score",
]
