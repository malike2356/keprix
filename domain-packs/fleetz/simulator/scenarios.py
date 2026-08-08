"""Fleetz telemetry/event simulator for contract and golden tests."""

from __future__ import annotations

import random
from typing import Any


def simulate_trip(*, fleet_id: str, vehicle_id: str, seed: int = 1) -> dict[str, Any]:
    rng = random.Random(seed)
    points = []
    lat, lon = 5.60, -0.18
    fuel = 80.0
    events = []
    for i in range(20):
        lat += rng.uniform(-0.001, 0.001)
        lon += rng.uniform(-0.001, 0.001)
        fuel -= rng.uniform(0.1, 0.4)
        points.append({"lat": lat, "lon": lon, "epoch_s": 1780000000 + i * 60, "fuel_l": round(fuel, 2)})
    return {
        "scenario": "normal_trip",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "points": points,
        "events": events,
    }


def simulate_refuel(*, fleet_id: str, vehicle_id: str) -> dict[str, Any]:
    return {
        "scenario": "refuel",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "samples": [
            {"epoch_s": 1780000000, "litres": 20.0},
            {"epoch_s": 1780000060, "litres": 70.0},
        ],
        "events": [{"id": "ev-refuel-1", "type": "fleetz.fuel.anomaly", "priority": 2}],
    }


def simulate_drain(*, fleet_id: str, vehicle_id: str) -> dict[str, Any]:
    return {
        "scenario": "drain",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "samples": [
            {"epoch_s": 1780000000, "litres": 70.0},
            {"epoch_s": 1780000120, "litres": 40.0},
        ],
        "events": [{"id": "ev-drain-1", "type": "fleetz.fuel.anomaly", "priority": 5}],
    }


def simulate_gps_gap(*, fleet_id: str, vehicle_id: str) -> dict[str, Any]:
    return {
        "scenario": "gps_gap",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "points": [{"lat": 5.6, "lon": -0.18, "epoch_s": 1780000000}],
        "gap_ratio": 0.7,
        "sample_count": 1,
        "unknown_distance": True,
    }


def simulate_sensor_drift(*, fleet_id: str, vehicle_id: str) -> dict[str, Any]:
    return {
        "scenario": "sensor_drift",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "calibration_age_days": 220,
        "sample_count": 30,
        "gap_ratio": 0.1,
        "spoof_flags": 0,
    }


def simulate_spoofing(*, fleet_id: str, vehicle_id: str) -> dict[str, Any]:
    return {
        "scenario": "spoofing",
        "fleet_id": fleet_id,
        "vehicle_id": vehicle_id,
        "spoof_flags": 2,
        "sample_count": 40,
        "gap_ratio": 0.05,
    }


def simulate_duplicate_out_of_order(*, fleet_id: str, vehicle_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "e1",
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "type": "fleetz.alert",
            "occurred_epoch_s": 100,
            "priority": 3,
        },
        {
            "id": "e1",
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "type": "fleetz.alert",
            "occurred_epoch_s": 100,
            "priority": 3,
        },
        {
            "id": "e2",
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "type": "fleetz.alert",
            "occurred_epoch_s": 90,
            "priority": 4,
        },
    ]


def simulate_storm(*, fleet_id: str, vehicle_id: str, n: int = 200) -> list[dict[str, Any]]:
    return [
        {
            "id": f"storm-{i}",
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "type": "telemetry.point",
            "occurred_epoch_s": 1780000000 + i,
            "priority": 1 if i % 50 else 8,
        }
        for i in range(n)
    ]


SCENARIOS = {
    "normal_trip": simulate_trip,
    "refuel": simulate_refuel,
    "drain": simulate_drain,
    "gps_gap": simulate_gps_gap,
    "sensor_drift": simulate_sensor_drift,
    "spoofing": simulate_spoofing,
}
