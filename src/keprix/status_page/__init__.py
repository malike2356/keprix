"""Keprix status page + incident communication (parity with shared/status)."""

from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal

OverallStatus = Literal["operational", "degraded", "outage", "maintenance"]
IncidentPhase = Literal["investigating", "identified", "monitoring", "resolved"]
IncidentSeverity = Literal["minor", "major", "critical"]

FAILURE_THRESHOLD = 3
RECOVERY_MS = 5 * 60 * 1000
MIN_LEAD_MS = 48 * 60 * 60 * 1000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def default_store_path() -> str:
    root = os.environ.get("KEPRIX_DATA_DIR") or str(Path.home() / ".keprix-data")
    return str(Path(root) / "status" / "status-store.json")


class MaintenanceConflictError(ValueError):
    pass


class MaintenanceLeadTimeError(ValueError):
    pass


class StatusStore:
    def __init__(
        self,
        file_path: str | None = None,
        *,
        product: str = "keprix",
        endpoints: list[dict[str, Any]] | None = None,
    ) -> None:
        self.file_path = file_path
        self.data = self._load(product, endpoints or [])

    def _load(self, product: str, endpoints: list[dict[str, Any]]) -> dict[str, Any]:
        if self.file_path and Path(self.file_path).exists():
            raw = json.loads(Path(self.file_path).read_text(encoding="utf-8"))
            return {
                "product": raw.get("product") or product,
                "endpoints": raw.get("endpoints") or endpoints,
                "incidents": raw.get("incidents") or [],
                "maintenance": raw.get("maintenance") or [],
                "pings": raw.get("pings") or [],
                "failureStreak": raw.get("failureStreak") or {},
                "recoverySince": raw.get("recoverySince") or {},
                "openIncidentByService": raw.get("openIncidentByService") or {},
            }
        return {
            "product": product,
            "endpoints": list(endpoints),
            "incidents": [],
            "maintenance": [],
            "pings": [],
            "failureStreak": {},
            "recoverySince": {},
            "openIncidentByService": {},
        }

    def persist(self) -> None:
        if not self.file_path:
            return
        path = Path(self.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def list_endpoints(self) -> list[dict[str, Any]]:
        return deepcopy(self.data["endpoints"])

    def set_endpoints(self, endpoints: list[dict[str, Any]]) -> None:
        self.data["endpoints"] = deepcopy(endpoints)
        self.persist()

    def record_ping(self, result: dict[str, Any]) -> None:
        self.data["pings"].insert(0, result)
        self.data["pings"] = self.data["pings"][:50_000]
        self.persist()

    def get_failure_streak(self, endpoint_id: str) -> int:
        return int(self.data["failureStreak"].get(endpoint_id) or 0)

    def set_failure_streak(self, endpoint_id: str, n: int) -> None:
        self.data["failureStreak"][endpoint_id] = n
        self.persist()

    def get_recovery_since(self, endpoint_id: str) -> str | None:
        return self.data["recoverySince"].get(endpoint_id)

    def set_recovery_since(self, endpoint_id: str, iso: str | None) -> None:
        self.data["recoverySince"][endpoint_id] = iso
        self.persist()

    def get_open_incident_id(self, service_id: str) -> str | None:
        return self.data["openIncidentByService"].get(service_id)

    def create_incident(
        self,
        *,
        title: str,
        affected_services: list[str],
        severity: IncidentSeverity = "major",
        auto_created: bool = False,
        message: str | None = None,
        detected_at: str | None = None,
    ) -> dict[str, Any]:
        now = detected_at or _now_iso()
        update = {
            "id": str(uuid.uuid4()),
            "phase": "investigating",
            "message": message
            or "Automated health checks detected an outage. Investigating.",
            "at": now,
        }
        incident = {
            "id": str(uuid.uuid4()),
            "title": title,
            "severity": severity,
            "phase": "investigating",
            "affectedServices": list(affected_services),
            "detectedAt": now,
            "autoCreated": auto_created,
            "updates": [update],
        }
        self.data["incidents"].insert(0, incident)
        for svc in affected_services:
            self.data["openIncidentByService"][svc] = incident["id"]
        self.persist()
        return deepcopy(incident)

    def add_incident_update(
        self,
        incident_id: str,
        phase: IncidentPhase,
        message: str,
        at: str | None = None,
    ) -> dict[str, Any] | None:
        row = next((i for i in self.data["incidents"] if i["id"] == incident_id), None)
        if not row:
            return None
        stamp = at or _now_iso()
        row["phase"] = phase
        row["updates"].append({"id": str(uuid.uuid4()), "phase": phase, "message": message, "at": stamp})
        if phase == "resolved":
            row["resolvedAt"] = stamp
            for svc in list(row["affectedServices"]):
                if self.data["openIncidentByService"].get(svc) == row["id"]:
                    del self.data["openIncidentByService"][svc]
        self.persist()
        return deepcopy(row)

    def get_incident(self, incident_id: str) -> dict[str, Any] | None:
        row = next((i for i in self.data["incidents"] if i["id"] == incident_id), None)
        return deepcopy(row) if row else None

    def list_incidents(self) -> list[dict[str, Any]]:
        return deepcopy(self.data["incidents"])

    def open_incidents(self) -> list[dict[str, Any]]:
        return [deepcopy(i) for i in self.data["incidents"] if i["phase"] != "resolved"]

    def list_maintenance(self) -> list[dict[str, Any]]:
        return deepcopy(self.data["maintenance"])

    def add_maintenance(self, window: dict[str, Any]) -> None:
        self.data["maintenance"].append(window)
        self.persist()

    def update_maintenance(self, window: dict[str, Any]) -> None:
        for idx, existing in enumerate(self.data["maintenance"]):
            if existing["id"] == window["id"]:
                self.data["maintenance"][idx] = window
                break
        self.persist()

    def service_health(self) -> list[dict[str, Any]]:
        out = []
        for ep in self.data["endpoints"]:
            streak = self.get_failure_streak(ep["id"])
            last = next((p for p in self.data["pings"] if p["endpointId"] == ep["id"]), None)
            health = "unknown"
            if last:
                health = "up" if last.get("ok") and streak == 0 else "down"
            out.append({"id": ep["id"], "name": ep["name"], "health": health})
        return out

    def compute_daily_uptime(self, days: int = 90) -> list[dict[str, Any]]:
        by_day: dict[str, dict[str, int]] = {}
        now = datetime.now(timezone.utc)
        for i in range(days):
            key = (now - timedelta(days=i)).date().isoformat()
            by_day[key] = {"ok": 0, "total": 0}
        for ping in self.data["pings"]:
            key = str(ping.get("at", ""))[:10]
            if key not in by_day:
                continue
            by_day[key]["total"] += 1
            if ping.get("ok"):
                by_day[key]["ok"] += 1
        rows = []
        for date in sorted(by_day.keys()):
            v = by_day[date]
            total = v["total"]
            ok = v["ok"]
            pct = 100.0 if total == 0 else round((ok / total) * 10000) / 100
            rows.append({"date": date, "okChecks": ok, "totalChecks": total, "uptimePct": pct})
        return rows

    def uptime_90d(self) -> float:
        daily = self.compute_daily_uptime(90)
        ok = sum(d["okChecks"] for d in daily)
        total = sum(d["totalChecks"] for d in daily)
        return 100.0 if total == 0 else round((ok / total) * 10000) / 100

    def derive_overall(self) -> OverallStatus:
        now = datetime.now(timezone.utc)
        for m in self.data["maintenance"]:
            start = _parse(m["startsAt"])
            end = _parse(m["endsAt"])
            if start <= now <= end:
                return "maintenance"
        open_rows = self.open_incidents()
        if any(i["severity"] in ("critical", "major") for i in open_rows):
            return "outage"
        if open_rows:
            return "degraded"
        if any(h["health"] == "down" for h in self.service_health()):
            return "degraded"
        return "operational"

    def snapshot(self) -> dict[str, Any]:
        upcoming = sorted(
            [m for m in self.list_maintenance() if _parse(m["endsAt"]) >= datetime.now(timezone.utc)],
            key=lambda m: m["startsAt"],
        )
        return {
            "product": self.data["product"],
            "overall": self.derive_overall(),
            "updatedAt": _now_iso(),
            "services": self.service_health(),
            "openIncidents": self.open_incidents(),
            "recentIncidents": self.list_incidents()[:20],
            "upcomingMaintenance": upcoming,
            "uptime90d": self.uptime_90d(),
            "dailyUptime": self.compute_daily_uptime(90),
        }


PingFn = Callable[[dict[str, Any]], dict[str, Any]]


def ping_endpoints(store: StatusStore, *, ping_fn: PingFn | None = None, now: str | None = None) -> list[dict[str, Any]]:
    import urllib.request

    at = now or _now_iso()
    results: list[dict[str, Any]] = []

    def _default(ep: dict[str, Any]) -> dict[str, Any]:
        expect = int(ep.get("expectStatus") or 200)
        try:
            req = urllib.request.Request(ep["url"], method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                code = getattr(resp, "status", 200)
                return {"ok": code == expect, "statusCode": code}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    fn = ping_fn or _default
    for ep in store.list_endpoints():
        raw = fn(ep)
        row = {
            "endpointId": ep["id"],
            "ok": bool(raw.get("ok")),
            "statusCode": raw.get("statusCode"),
            "latencyMs": raw.get("latencyMs"),
            "error": raw.get("error"),
            "at": raw.get("at") or at,
        }
        store.record_ping(row)
        results.append(row)
    return results


def detect_outage(store: StatusStore, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in results:
        if r["ok"]:
            store.set_failure_streak(r["endpointId"], 0)
            continue
        n = store.get_failure_streak(r["endpointId"]) + 1
        store.set_failure_streak(r["endpointId"], n)
        if n >= FAILURE_THRESHOLD:
            out.append({"endpointId": r["endpointId"], "failures": n})
    return out


def auto_create_incident(store: StatusStore, endpoint_ids: list[str], *, now: str | None = None) -> dict[str, Any] | None:
    eps = [e for e in store.list_endpoints() if e["id"] in endpoint_ids]
    if not eps:
        return None
    if all(store.get_open_incident_id(e["id"]) for e in eps):
        oid = store.get_open_incident_id(eps[0]["id"])
        return store.get_incident(oid) if oid else None
    names = ", ".join(e["name"] for e in eps)
    return store.create_incident(
        title=f"Outage detected: {names}",
        severity="critical" if len(eps) > 1 else "major",
        affected_services=[e["id"] for e in eps],
        auto_created=True,
        message=f"Health monitor recorded {FAILURE_THRESHOLD}+ consecutive failures for: {names}.",
        detected_at=now,
    )


def resolve_incident(
    store: StatusStore,
    results: list[dict[str, Any]],
    *,
    now: str | None = None,
    recovery_ms: int = RECOVERY_MS,
) -> list[dict[str, Any]]:
    now_iso = now or _now_iso()
    now_ms = int(_parse(now_iso).timestamp() * 1000)
    resolved: list[dict[str, Any]] = []
    for r in results:
        if not r["ok"]:
            store.set_recovery_since(r["endpointId"], None)
            continue
        open_id = store.get_open_incident_id(r["endpointId"])
        if not open_id:
            store.set_recovery_since(r["endpointId"], None)
            continue
        since = store.get_recovery_since(r["endpointId"])
        if not since:
            store.set_recovery_since(r["endpointId"], now_iso)
            since = now_iso
        since_ms = int(_parse(since).timestamp() * 1000)
        if now_ms - since_ms >= recovery_ms:
            incident = store.add_incident_update(
                open_id,
                "resolved",
                f"Service recovered. Health checks succeeded for {recovery_ms // 60000}+ minutes.",
                at=now_iso,
            )
            if incident:
                resolved.append(incident)
            store.set_recovery_since(r["endpointId"], None)
    return resolved


def run_health_cycle(
    store: StatusStore,
    *,
    ping_fn: PingFn | None = None,
    now: str | None = None,
    recovery_ms: int = RECOVERY_MS,
) -> dict[str, Any]:
    pings = ping_endpoints(store, ping_fn=ping_fn, now=now)
    outages = detect_outage(store, pings)
    created = None
    if outages:
        created = auto_create_incident(store, [o["endpointId"] for o in outages], now=now)
    resolved = resolve_incident(store, pings, now=now, recovery_ms=recovery_ms)
    return {"pings": pings, "outages": outages, "created": created, "resolved": resolved}


def schedule_maintenance(
    store: StatusStore,
    *,
    title: str,
    description: str,
    affected_services: list[str],
    starts_at: str,
    ends_at: str,
    emergency: bool = False,
    now: str | None = None,
) -> dict[str, Any]:
    start = _parse(starts_at)
    end = _parse(ends_at)
    if end <= start:
        raise ValueError("Invalid maintenance window: endsAt must be after startsAt")
    now_dt = _parse(now or _now_iso())
    if not emergency and (start - now_dt).total_seconds() * 1000 < MIN_LEAD_MS:
        raise MaintenanceLeadTimeError(
            "Non-emergency maintenance must be announced at least 48 hours in advance"
        )
    for existing in store.list_maintenance():
        a0, a1 = _parse(existing["startsAt"]), _parse(existing["endsAt"])
        if a0 < end and start < a1:
            raise MaintenanceConflictError(
                f"Overlaps existing maintenance \"{existing['title']}\" ({existing['startsAt']} - {existing['endsAt']})"
            )
    window = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "affectedServices": list(affected_services),
        "startsAt": starts_at,
        "endsAt": ends_at,
        "announcedAt": now or _now_iso(),
        "remindersSent": [],
    }
    store.add_maintenance(window)
    return window


def maintenance_calendar(store: StatusStore) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    return sorted(
        [m for m in store.list_maintenance() if _parse(m["endsAt"]) >= now],
        key=lambda m: m["startsAt"],
    )


class NotificationLog:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def push(self, row: dict[str, Any]) -> None:
        self.records.insert(0, row)


def notify_active_users(
    incident: dict[str, Any],
    emails: list[str],
    *,
    log: NotificationLog | None = None,
) -> dict[str, Any]:
    log = log or NotificationLog()
    row = {
        "id": str(uuid.uuid4()),
        "channel": "email_active_users",
        "template": "incident_detected",
        "incidentId": incident["id"],
        "recipients": list(emails),
        "subject": f"[Status] Incident detected: {incident['title']}",
        "body": f"Detected at {incident['detectedAt']}. Phase: {incident['phase']}.",
        "at": _now_iso(),
    }
    log.push(row)
    return row


_STORE: StatusStore | None = None
_LOG = NotificationLog()


def get_store() -> StatusStore:
    global _STORE
    if _STORE is None:
        endpoints = [
            {
                "id": "keprix-api",
                "name": "Keprix API",
                "url": os.environ.get("KEPRIX_STATUS_API_URL") or "https://app.keprixai.com/api/health",
            },
            {
                "id": "keprix-web",
                "name": "Keprix web",
                "url": os.environ.get("KEPRIX_STATUS_WEB_URL") or "https://keprixai.com/",
            },
        ]
        _STORE = StatusStore(os.environ.get("KEPRIX_STATUS_STORE_PATH") or default_store_path(), product="keprix", endpoints=endpoints)
        if not _STORE.list_endpoints():
            _STORE.set_endpoints(endpoints)
    return _STORE


def get_notification_log() -> NotificationLog:
    return _LOG
