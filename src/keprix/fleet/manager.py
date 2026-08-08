"""Fleet management for managed keprix operations."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

InstanceStatus = Literal["healthy", "degraded", "unreachable", "update_available"]


def _fleet_dir() -> Path:
    path = Path.home() / ".keprix" / "fleet"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FleetInstance:
    id: str
    name: str
    base_url: str
    version: str = "0.0.0"
    status: InstanceStatus = "healthy"
    last_seen_at: str = field(default_factory=_utcnow)
    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    disk_pct: float = 0.0
    alerts: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "version": self.version,
            "status": self.status,
            "last_seen_at": self.last_seen_at,
            "cpu_pct": self.cpu_pct,
            "ram_pct": self.ram_pct,
            "disk_pct": self.disk_pct,
            "alerts": self.alerts,
        }


class FleetManager:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _fleet_dir()
        self.instances_path = self.base_dir / "instances.json"
        self.audit_path = self.base_dir / "audit.jsonl"

    def _load(self) -> list[dict[str, Any]]:
        if not self.instances_path.exists():
            return []
        return json.loads(self.instances_path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self.instances_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def register(self, *, name: str, base_url: str, version: str = "0.0.0") -> dict[str, Any]:
        rows = self._load()
        row = FleetInstance(id=str(uuid.uuid4()), name=name, base_url=base_url.rstrip("/"), version=version).to_dict()
        rows.append(row)
        self._save(rows)
        self.audit("register", {"instance_id": row["id"], "name": name})
        return row

    def list_instances(self) -> list[dict[str, Any]]:
        return self._load()

    def get_instance(self, instance_id: str) -> dict[str, Any] | None:
        for row in self._load():
            if row["id"] == instance_id:
                return row
        return None

    def remove(self, instance_id: str) -> bool:
        rows = self._load()
        kept = [row for row in rows if row.get("id") != instance_id]
        if len(kept) == len(rows):
            return False
        self._save(kept)
        self.audit("remove", {"instance_id": instance_id})
        return True

    def probe_health(self, instance_id: str, *, timeout_s: float = 5.0) -> dict[str, Any] | None:
        """Server-side health pull against the instance base_url."""
        row = self.get_instance(instance_id)
        if row is None:
            return None
        base = str(row.get("base_url") or "").rstrip("/")
        reachable = False
        version = str(row.get("version") or "0.0.0")
        alerts = int(row.get("alerts") or 0)
        try:
            import urllib.request

            req = urllib.request.Request(f"{base}/api/health", method="GET")
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310
                reachable = 200 <= int(getattr(resp, "status", 200) or 200) < 300
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    payload = {}
                if isinstance(payload, dict):
                    version = str(payload.get("version") or payload.get("keprix_version") or version)
                    alerts = int(payload.get("alerts") or alerts)
        except Exception:
            reachable = False
        return self.record_health(
            instance_id,
            metrics={
                "reachable": reachable,
                "version": version,
                "alerts": alerts,
                "cpu_pct": float(row.get("cpu_pct") or 0),
                "ram_pct": float(row.get("ram_pct") or 0),
                "disk_pct": float(row.get("disk_pct") or 0),
            },
        )

    def record_health(self, instance_id: str, *, metrics: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._load()
        for index, row in enumerate(rows):
            if row["id"] != instance_id:
                continue
            cpu = float(metrics.get("cpu_pct") or 0)
            ram = float(metrics.get("ram_pct") or 0)
            disk = float(metrics.get("disk_pct") or 0)
            status: InstanceStatus = "healthy"
            if metrics.get("reachable") is False:
                status = "unreachable"
            elif cpu > 90 or ram > 90 or disk > 90:
                status = "degraded"
            elif metrics.get("update_available"):
                status = "update_available"
            row.update(
                {
                    "cpu_pct": cpu,
                    "ram_pct": ram,
                    "disk_pct": disk,
                    "status": status,
                    "last_seen_at": _utcnow(),
                    "alerts": int(metrics.get("alerts") or 0),
                    "version": str(metrics.get("version") or row.get("version") or "0.0.0"),
                }
            )
            rows[index] = row
            self._save(rows)
            return row
        return None

    def audit(self, action: str, payload: dict[str, Any]) -> None:
        record = {"at": _utcnow(), "action": action, "payload": payload}
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
        return rows[-limit:]


_manager: FleetManager | None = None


def get_fleet_manager() -> FleetManager:
    global _manager
    if _manager is None:
        _manager = FleetManager()
    return _manager
