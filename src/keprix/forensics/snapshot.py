"""Forensic snapshot capture with hash chain."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix_cli.config import get_keprix_home


def _snapshots_dir() -> Path:
    return get_keprix_home() / "forensics" / "snapshots"


def _chain_path() -> Path:
    return get_keprix_home() / "forensics" / "chain.jsonl"


def _last_chain_hash() -> str:
    path = _chain_path()
    if not path.exists():
        return "genesis"
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return "genesis"
    try:
        return str(json.loads(lines[-1]).get("hash") or "genesis")
    except Exception:
        return "genesis"


def capture_snapshot(
    *,
    session_id: str | None = None,
    reason: str = "manual",
    product_id: str | None = None,
) -> dict[str, Any]:
    from keprix.incident.response import is_vault_sealed
    from keprix.incident.store import list_incidents
    from keprix.security.product_policy import list_policies
    from keprix.security.scout_control import snapshot as control_snapshot
    from keprix.security.scout_correlation import _read_recent_events
    from keprix.security.scout_metrics import product_metrics
    from keprix.security.scout_registration import ScoutRegistration

    snapshot_id = f"ckpt-{uuid.uuid4().hex[:12]}"
    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    body: dict[str, Any] = {
        "id": snapshot_id,
        "captured_at": captured_at,
        "reason": reason,
        "session_id": session_id,
        "product_id": product_id,
        "control_state": control_snapshot(),
        "vault_sealed": is_vault_sealed(),
        "open_incidents": list_incidents(),
        "product_policies": list_policies(),
        "product_metrics": product_metrics(),
        "registered_agents": ScoutRegistration().list_local_registrations(),
        "recent_signals": _read_recent_events(limit=100),
    }
    if session_id:
        body["recent_signals"] = [
            row for row in body["recent_signals"] if row.get("session_id") == session_id
        ] or body["recent_signals"]

    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    prev_hash = _last_chain_hash()
    digest = hashlib.sha256(f"{prev_hash}:{canonical}".encode("utf-8")).hexdigest()
    body["prev_hash"] = prev_hash
    body["hash"] = digest

    out_dir = _snapshots_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{snapshot_id}.json"
    out_path.write_text(json.dumps(body, indent=2), encoding="utf-8")

    chain_path = _chain_path()
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with chain_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "snapshot_id": snapshot_id,
                    "captured_at": captured_at,
                    "prev_hash": prev_hash,
                    "hash": digest,
                    "reason": reason,
                }
            )
            + "\n"
        )
    return body


def list_snapshots() -> list[dict[str, Any]]:
    out_dir = _snapshots_dir()
    if not out_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(out_dir.glob("ckpt-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "id": payload.get("id") or path.stem,
                    "captured_at": payload.get("captured_at"),
                    "reason": payload.get("reason"),
                    "session_id": payload.get("session_id"),
                    "hash": payload.get("hash"),
                }
            )
        except Exception:
            continue
    rows.sort(key=lambda row: str(row.get("captured_at") or ""), reverse=True)
    return rows


def load_snapshot(snapshot_id: str) -> dict[str, Any]:
    path = _snapshots_dir() / f"{snapshot_id}.json"
    if not path.exists():
        raise FileNotFoundError(snapshot_id)
    return json.loads(path.read_text(encoding="utf-8"))


def export_snapshot(snapshot_id: str, *, output: Path | None = None) -> Path:
    payload = load_snapshot(snapshot_id)
    out = output or (_snapshots_dir() / "exports" / f"{snapshot_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def analyze_snapshot(snapshot_id: str) -> dict[str, Any]:
    payload = load_snapshot(snapshot_id)
    signals = payload.get("recent_signals") or []
    critical = sum(1 for row in signals if str(row.get("severity")).lower() in {"critical", "emergency"})
    products = sorted({str(row.get("product") or "keprix") for row in signals})
    recommendations: list[str] = []
    if critical >= 3:
        recommendations.append("Review correlated critical signals and consider session suspension")
    if payload.get("vault_sealed"):
        recommendations.append("Vault is sealed; verify rotation before unsealing")
    if payload.get("control_state", {}).get("egress_force_blocked"):
        recommendations.append("Egress is blocked; plan gradual re-enable after containment")
    return {
        "snapshot_id": snapshot_id,
        "signal_count": len(signals),
        "critical_signals": critical,
        "products_seen": products,
        "open_incidents": len(payload.get("open_incidents") or []),
        "recommendations": recommendations or ["No immediate automated recommendations"],
    }
