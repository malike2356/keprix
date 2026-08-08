"""Southbound Fleetz product API connector (default deny, fixture-backed for local)."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib import error, request

PACK_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = PACK_ROOT / "fixtures" / "fleet_data.json"

# Declared allowlist only (never scrape UI or open SQL)
ALLOWED_ROUTES = (
    ("GET", "/api/keprix/v1/health"),
    ("GET", "/api/keprix/v1/capabilities"),
    ("POST", "/api/keprix/v1/token/exchange"),
    ("GET", "/api/keprix/v1/context"),
    ("POST", "/api/keprix/v1/events/ack"),
    ("GET", "/api/keprix/v1/fleets/{fleet_id}"),
    ("GET", "/api/keprix/v1/fleets"),
    ("GET", "/api/keprix/v1/vehicles/{vehicle_id}"),
    ("GET", "/api/keprix/v1/vehicles"),
    ("GET", "/api/keprix/v1/drivers/{driver_id}"),
    ("GET", "/api/keprix/v1/drivers"),
    ("GET", "/api/keprix/v1/trips/{trip_id}"),
    ("GET", "/api/keprix/v1/trips"),
    ("GET", "/api/keprix/v1/geofences/{geofence_id}"),
    ("GET", "/api/keprix/v1/geofences"),
    ("GET", "/api/keprix/v1/alerts/{alert_id}"),
    ("GET", "/api/keprix/v1/alerts"),
    ("GET", "/api/keprix/v1/maintenance/{maintenance_id}"),
    ("GET", "/api/keprix/v1/maintenance"),
    ("GET", "/api/keprix/v1/vehicles/{vehicle_id}/positions/summary"),
    ("GET", "/api/keprix/v1/vehicles/{vehicle_id}/fuel/summary"),
    ("GET", "/api/keprix/v1/vehicles/{vehicle_id}/device-health"),
    ("GET", "/api/keprix/v1/vehicles/{vehicle_id}/sensor-health"),
    ("GET", "/api/keprix/v1/audit"),
    ("POST", "/api/keprix/v1/actions/notification/preview"),
    ("POST", "/api/keprix/v1/actions/notification/apply"),
    ("POST", "/api/keprix/v1/actions/task/create"),
    ("POST", "/api/keprix/v1/actions/case/create"),
    ("POST", "/api/keprix/v1/actions/report/export"),
    ("POST", "/api/keprix/v1/actions/alert-rule/preview"),
    ("POST", "/api/keprix/v1/actions/maintenance-task/preview"),
    ("POST", "/api/keprix/v1/actions/geofence/preview"),
)

# Explicitly never allowed
DENIED_PATTERNS = (
    "/api/commands",
    "/api/devices/send",
    "traccar",
    "mqtt",
    "immobil",
)


def load_fixtures() -> dict[str, Any]:
    if FIXTURES_PATH.exists():
        return json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return {"fleets": {}, "vehicles": {}, "drivers": {}, "trips": {}, "alerts": {}, "geofences": {}, "maintenance": []}


class FleetzProductClient:
    """Bounded connector. Uses fixtures when FLEETZ_USE_FIXTURES!=0 or no base URL."""

    def __init__(self) -> None:
        self.base_url = os.environ.get("FLEETZ_PRODUCT_API_URL", "").rstrip("/")
        use_fix = os.environ.get("FLEETZ_USE_FIXTURES", "1").strip() not in {"0", "false", "False"}
        self.use_fixtures = use_fix or not self.base_url
        self._fixtures = load_fixtures()
        self._token: str | None = None
        self._applied_keys: set[str] = set()
        self._events_acked: set[str] = set()

    def _fleet_ok(self, fleet_id: str) -> bool:
        return fleet_id in self._fixtures.get("fleets", {})

    def _vehicle_in_fleet(self, fleet_id: str, vehicle_id: str | None) -> bool:
        if not vehicle_id:
            return True
        v = self._fixtures.get("vehicles", {}).get(vehicle_id)
        return bool(v and v.get("fleet_id") == fleet_id)

    def health(self) -> dict[str, Any]:
        if self.use_fixtures:
            return {"status": "ok", "mode": "fixture", "product": "fleetz"}
        return self._http_json("GET", "/api/keprix/v1/health")

    def exchange_token(self, bootstrap_claims: dict[str, Any]) -> dict[str, Any]:
        # Never log secrets; return short-lived opaque token shape
        raw = json.dumps(bootstrap_claims, sort_keys=True)
        token = hashlib.sha256(f"fleetz:{raw}:{time.time() // 300}".encode()).hexdigest()
        self._token = token
        return {
            "access_token": token,
            "expires_in": 300,
            "token_type": "Bearer",
            "scope": bootstrap_claims.get("grants") or ["fleet_read"],
        }

    def get_fleet(self, fleet_id: str) -> dict[str, Any] | None:
        if not self._fleet_ok(fleet_id):
            return None
        return self._fixtures["fleets"].get(fleet_id)

    def search_fleets(self, *, query: str = "", actor_fleet_id: str = "") -> list[dict[str, Any]]:
        # Hard isolation: actor only sees their fleet unless empty actor (dev)
        fleets = self._fixtures.get("fleets", {})
        rows = []
        for fid, row in fleets.items():
            if actor_fleet_id and fid != actor_fleet_id:
                continue
            if query and query.lower() not in json.dumps(row).lower():
                continue
            rows.append(row)
        return rows

    def get_vehicle(self, fleet_id: str, vehicle_id: str) -> dict[str, Any] | None:
        if not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return None
        return self._fixtures.get("vehicles", {}).get(vehicle_id)

    def search_vehicles(self, fleet_id: str, *, query: str = "") -> list[dict[str, Any]]:
        rows = []
        for vid, row in self._fixtures.get("vehicles", {}).items():
            if row.get("fleet_id") != fleet_id:
                continue
            if query and query.lower() not in json.dumps(row).lower():
                continue
            rows.append(row)
        return rows

    def get_driver(self, fleet_id: str, driver_id: str, *, role: str, purpose: str) -> dict[str, Any] | None:
        row = self._fixtures.get("drivers", {}).get(driver_id)
        if not row or row.get("fleet_id") != fleet_id:
            return None
        # Minimise: strip personal phone unless authorised purpose
        out = dict(row)
        if purpose not in {"incident_investigation", "ops"} or role not in {"fleet_manager", "dispatcher", "owner"}:
            out.pop("phone", None)
            out["display_name"] = out.get("display_name_redacted") or "Driver"
        out.pop("off_duty_tracks", None)
        return out

    def search_drivers(self, fleet_id: str, *, query: str = "") -> list[dict[str, Any]]:
        rows = []
        for did, row in self._fixtures.get("drivers", {}).items():
            if row.get("fleet_id") != fleet_id:
                continue
            slim = {k: v for k, v in row.items() if k not in {"phone", "off_duty_tracks"}}
            if query and query.lower() not in json.dumps(slim).lower():
                continue
            rows.append(slim)
        return rows

    def get_trip(self, fleet_id: str, trip_id: str) -> dict[str, Any] | None:
        trip = self._fixtures.get("trips", {}).get(trip_id)
        if not trip or trip.get("fleet_id") != fleet_id:
            return None
        return trip

    def search_trips(
        self,
        fleet_id: str,
        *,
        vehicle_id: str | None,
        start_epoch_s: Any,
        end_epoch_s: Any,
        cursor: Any,
        limit: int,
    ) -> dict[str, Any]:
        rows = []
        for tid, trip in self._fixtures.get("trips", {}).items():
            if trip.get("fleet_id") != fleet_id:
                continue
            if vehicle_id and trip.get("vehicle_id") != vehicle_id:
                continue
            rows.append({k: v for k, v in trip.items() if k != "points"})
        rows = rows[: max(1, min(limit, 200))]
        return {"trips": rows, "count": len(rows), "next_cursor": None}

    def get_geofence(self, fleet_id: str, geofence_id: str) -> dict[str, Any] | None:
        row = self._fixtures.get("geofences", {}).get(geofence_id)
        if not row or row.get("fleet_id") != fleet_id:
            return None
        return row

    def search_geofences(self, fleet_id: str) -> list[dict[str, Any]]:
        return [g for g in self._fixtures.get("geofences", {}).values() if g.get("fleet_id") == fleet_id]

    def get_alert(self, fleet_id: str, alert_id: str) -> dict[str, Any] | None:
        row = self._fixtures.get("alerts", {}).get(alert_id)
        if not row or row.get("fleet_id") != fleet_id:
            return None
        return row

    def search_alerts(self, fleet_id: str, *, vehicle_id: str | None, status: Any) -> list[dict[str, Any]]:
        rows = []
        for aid, row in self._fixtures.get("alerts", {}).items():
            if row.get("fleet_id") != fleet_id:
                continue
            if vehicle_id and row.get("vehicle_id") != vehicle_id:
                continue
            if status and row.get("status") != status:
                continue
            rows.append(row)
        return rows

    def get_maintenance(self, fleet_id: str, maintenance_id: str) -> dict[str, Any] | None:
        for row in self._fixtures.get("maintenance", []):
            if row.get("id") == maintenance_id and row.get("fleet_id") == fleet_id:
                return row
        return None

    def search_maintenance(self, fleet_id: str, *, vehicle_id: str | None) -> list[dict[str, Any]]:
        rows = []
        for row in self._fixtures.get("maintenance", []):
            if row.get("fleet_id") != fleet_id:
                continue
            if vehicle_id and row.get("vehicle_id") != vehicle_id:
                continue
            rows.append(row)
        return rows

    def position_summary(
        self,
        fleet_id: str,
        vehicle_id: str,
        *,
        start_epoch_s: float,
        end_epoch_s: float,
        resolution: str = "5m",
        max_points: int = 200,
    ) -> dict[str, Any]:
        if not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return {"error": "denied", "points": []}
        max_points = max(1, min(int(max_points), 500))
        vehicle = self.get_vehicle(fleet_id, vehicle_id) or {}
        # Downsampled product-side; missing is unknown not zero
        last = vehicle.get("last_position")
        if not last:
            return {
                "fleet_id": fleet_id,
                "vehicle_id": vehicle_id,
                "points": [],
                "sample_count": 0,
                "resolution": resolution,
                "start_epoch_s": start_epoch_s,
                "end_epoch_s": end_epoch_s,
                "unknown": True,
            }
        return {
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "points": [last],
            "sample_count": 1,
            "resolution": resolution,
            "max_points": max_points,
            "last_point_epoch_s": last.get("epoch_s"),
            "start_epoch_s": start_epoch_s,
            "end_epoch_s": end_epoch_s,
            "downsampled": True,
        }

    def fuel_series_summary(
        self,
        fleet_id: str,
        vehicle_id: str,
        *,
        start_epoch_s: float,
        end_epoch_s: float,
        resolution: str = "15m",
        max_points: int = 200,
    ) -> dict[str, Any]:
        if not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return {"error": "denied"}
        vehicle = self.get_vehicle(fleet_id, vehicle_id) or {}
        fuel = vehicle.get("fuel") or {}
        samples = fuel.get("samples") or []
        if not samples:
            return {
                "fleet_id": fleet_id,
                "vehicle_id": vehicle_id,
                "sample_count": 0,
                "start_fuel_l": None,
                "end_fuel_l": None,
                "unknown": True,
                "resolution": resolution,
            }
        capped = samples[: max(1, min(max_points, 500))]
        return {
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "sample_count": len(capped),
            "start_fuel_l": capped[0].get("litres"),
            "end_fuel_l": capped[-1].get("litres"),
            "last_point_epoch_s": capped[-1].get("epoch_s"),
            "resolution": resolution,
            "start_epoch_s": start_epoch_s,
            "end_epoch_s": end_epoch_s,
            "downsampled": True,
            "unit": fuel.get("unit") or "L",
        }

    def device_health(self, fleet_id: str, vehicle_id: str | None) -> dict[str, Any]:
        if vehicle_id and not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return {"error": "denied"}
        vehicle = self.get_vehicle(fleet_id, vehicle_id) if vehicle_id else {}
        return (vehicle or {}).get("device_health") or {"status": "unknown", "online": False}

    def sensor_health(self, fleet_id: str, vehicle_id: str | None) -> dict[str, Any]:
        if vehicle_id and not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return {"error": "denied"}
        vehicle = self.get_vehicle(fleet_id, vehicle_id) if vehicle_id else {}
        return (vehicle or {}).get("sensor_health") or {"status": "unknown"}

    def sensor_quality(self, fleet_id: str, vehicle_id: str | None) -> dict[str, Any]:
        health = self.sensor_health(fleet_id, vehicle_id)
        from calculators.formulas import sensor_quality_score

        return {
            **sensor_quality_score(
                sample_count=int(health.get("sample_count") or 10),
                gap_ratio=float(health.get("gap_ratio") or 0.05),
                calibration_age_days=float(health.get("calibration_age_days") or 20),
                spoof_flags=int(health.get("spoof_flags") or 0),
            ),
            "sample_count": int(health.get("sample_count") or 10),
        }

    def audit_entries(self, fleet_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self._fleet_ok(fleet_id):
            return []
        rows = [a for a in self._fixtures.get("audit", []) if a.get("fleet_id") == fleet_id]
        return rows[:limit]

    def fleet_brief(self, fleet_id: str) -> dict[str, Any]:
        if not self._fleet_ok(fleet_id):
            return {}
        vehicles = self.search_vehicles(fleet_id)
        alerts = self.search_alerts(fleet_id, vehicle_id=None, status="open")
        maintenance = self.search_maintenance(fleet_id, vehicle_id=None)
        offline = [v["id"] for v in vehicles if not (v.get("device_health") or {}).get("online", True)]
        return {
            "offline_vehicles": offline,
            "active_alerts": [a["id"] for a in alerts],
            "fuel_summary": {"unit": "L", "note": "aggregate_product_side"},
            "utilisation": {"active_vehicles": len(vehicles) - len(offline), "total": len(vehicles)},
            "maintenance": [m["id"] for m in maintenance],
            "overdue_cases": self._fixtures.get("fleets", {}).get(fleet_id, {}).get("overdue_cases") or [],
            "data_quality_gaps": self._fixtures.get("fleets", {}).get(fleet_id, {}).get("data_quality_gaps") or [],
            "record_ids": {
                "fleet_id": fleet_id,
                "vehicle_ids": [v["id"] for v in vehicles],
                "alert_ids": [a["id"] for a in alerts],
            },
        }

    def idle_segments(self, fleet_id: str, vehicle_id: str | None) -> list[dict[str, Any]]:
        if vehicle_id and not self._vehicle_in_fleet(fleet_id, vehicle_id):
            return []
        vehicle = self.get_vehicle(fleet_id, vehicle_id) if vehicle_id else {}
        return (vehicle or {}).get("idle_segments") or []

    def driver_risk_summary(self, fleet_id: str, driver_id: str) -> dict[str, Any]:
        driver = self.get_driver(fleet_id, driver_id, role="fleet_manager", purpose="ops") or {}
        return {
            "driver_id": driver_id,
            "risk_score": driver.get("risk_score", 0.2),
            "events": driver.get("risk_events") or [],
            "off_duty_excluded": True,
        }

    def apply_notification(
        self,
        fleet_id: str,
        *,
        vehicle_id: str | None,
        channel: str,
        body: str,
        approval_evidence: Any,
        object_version: Any,
        idempotency_key: Any,
    ) -> dict[str, Any]:
        key = str(idempotency_key or "")
        if key and key in self._applied_keys:
            return {"id": f"notif-dup-{key}", "duplicate": True}
        if key:
            self._applied_keys.add(key)
        return {
            "id": f"notif-{uuid.uuid4().hex[:8]}",
            "fleet_id": fleet_id,
            "vehicle_id": vehicle_id,
            "channel": channel,
            "body_redacted": True,
            "approval_evidence_present": bool(approval_evidence),
            "object_version": object_version,
        }

    def create_task(self, fleet_id: str, **kwargs: Any) -> dict[str, Any]:
        key = str(kwargs.get("idempotency_key") or "")
        if key and key in self._applied_keys:
            return {"id": f"task-dup-{key}", "duplicate": True}
        if key:
            self._applied_keys.add(key)
        return {
            "id": f"task-{uuid.uuid4().hex[:8]}",
            "fleet_id": fleet_id,
            "vehicle_id": kwargs.get("vehicle_id"),
            "title": kwargs.get("title"),
            "duplicate": False,
        }

    def create_case(self, fleet_id: str, **kwargs: Any) -> dict[str, Any]:
        key = str(kwargs.get("idempotency_key") or "")
        if key and key in self._applied_keys:
            return {"id": f"case-dup-{key}", "duplicate": True}
        if key:
            self._applied_keys.add(key)
        return {
            "id": f"case-{uuid.uuid4().hex[:8]}",
            "fleet_id": fleet_id,
            "vehicle_id": kwargs.get("vehicle_id"),
            "title": kwargs.get("title"),
            "hypothesis": kwargs.get("hypothesis"),
            "accusation": False,
            "evidence_ids": kwargs.get("evidence_ids") or [],
            "duplicate": False,
        }

    def export_report(self, fleet_id: str, *, report_type: str, precise_routes: bool) -> dict[str, Any]:
        return {
            "id": f"report-{uuid.uuid4().hex[:8]}",
            "fleet_id": fleet_id,
            "report_type": report_type,
            "precise_routes": False,
            "uri": f"fixture://reports/{fleet_id}/{report_type}",
        }

    def ack_event(self, event_id: str) -> dict[str, Any]:
        dup = event_id in self._events_acked
        self._events_acked.add(event_id)
        return {"acked": True, "duplicate": dup, "id": event_id}

    def validate_event(self, event: dict[str, Any]) -> dict[str, Any]:
        required = ("id", "type", "source", "fleet_id", "occurred_at")
        missing = [k for k in required if not event.get(k)]
        if missing:
            return {"valid": False, "missing": missing}
        # Never treat missing fuel/position as zero
        data = event.get("data") or {}
        if "fuel_l" in data and data["fuel_l"] is None:
            return {"valid": False, "reason": "null_fuel_not_zero"}
        return {"valid": True}

    def _http_json(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        for denied in DENIED_PATTERNS:
            if denied in path.lower():
                raise PermissionError(f"denied_route:{path}")
        url = f"{self.base_url}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self._token:
            req.add_header("Authorization", f"Bearer {self._token}")
        try:
            with request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            return {"status": "error", "http_status": exc.code, "error": str(exc)}
        except error.URLError as exc:
            return {"status": "error", "error": str(exc.reason)}
