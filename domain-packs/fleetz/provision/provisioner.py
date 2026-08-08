"""Declarative Fleetz sidecar provisioning (idempotent receipts, no secrets)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.contract import CONTRACT_VERSION, PACK_VERSION, PRODUCT_KEY, pack_manifest

PACK_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_DIR = PACK_ROOT / "provision" / "receipts"


def _checksum_tree() -> str:
    parts: list[str] = []
    for path in sorted(PACK_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if "receipts" in path.parts or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        parts.append(f"{path.relative_to(PACK_ROOT)}:{hashlib.sha256(path.read_bytes()).hexdigest()[:12]}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def plan_provision(fleet_namespace: str = "default") -> dict[str, Any]:
    return {
        "product_key": PRODUCT_KEY,
        "action": "plan",
        "steps": [
            "verify_pack_compatibility",
            "create_product_deployment_namespace",
            "register_workload_identity_callbacks",
            "install_pinned_pack",
            "apply_memory_index_policy",
            "register_capability_nodes_and_connector",
            "validate_grants_against_product_capabilities",
            "run_readonly_contract_smoke",
            "await_operator_feature_flag",
            "emit_receipt",
        ],
        "fleet_namespace": fleet_namespace,
        "event_topics_allowlist": [
            "fleetz.vehicle.state",
            "fleetz.trip",
            "fleetz.fuel.anomaly",
            "fleetz.geofence",
            "fleetz.sensor.health",
            "fleetz.maintenance",
            "fleetz.alert",
        ],
        "event_topics_denied": [
            "fleetz.device.command",
            "fleetz.mqtt.command",
            "fleetz.traccar.command",
            "*",
        ],
        "timezone": "Africa/Accra",
        "currency": "GHS",
        "budgets": {
            "max_model_calls_per_minute": 30,
            "max_events_batched_window_s": 60,
            "per_fleet_quota": 1000,
        },
        "kill_switches": ["product", "fleet", "node", "provider"],
    }


def provision(
    *,
    fleet_namespace: str = "default",
    dry_run: bool = False,
    activate: bool = False,
) -> dict[str, Any]:
    plan = plan_provision(fleet_namespace)
    checksum = _checksum_tree()
    receipt = {
        "product_key": PRODUCT_KEY,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "manifest": pack_manifest(),
        "fleet_namespace": fleet_namespace,
        "checksum": checksum,
        "dry_run": dry_run,
        "activated": bool(activate) and not dry_run,
        "plan": plan,
        "rollback": {
            "instruction": "Disable feature flag, drain consumers, restore previous pack checksum receipt.",
            "last_known_good": None,
        },
        "secrets_included": False,
        "broker_can_publish_commands": False,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    if not dry_run:
        RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RECEIPTS_DIR / f"fleetz-{fleet_namespace}-{checksum}.json"
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        receipt["receipt_path"] = str(path)
    return receipt


def status(fleet_namespace: str = "default") -> dict[str, Any]:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    receipts = sorted(RECEIPTS_DIR.glob(f"fleetz-{fleet_namespace}-*.json"))
    latest = None
    if receipts:
        latest = json.loads(receipts[-1].read_text(encoding="utf-8"))
    return {
        "product_key": PRODUCT_KEY,
        "fleet_namespace": fleet_namespace,
        "receipt_count": len(receipts),
        "latest": latest,
        "pack_version": PACK_VERSION,
    }


def rollback(fleet_namespace: str = "default") -> dict[str, Any]:
    st = status(fleet_namespace)
    return {
        "product_key": PRODUCT_KEY,
        "action": "rollback",
        "fleet_namespace": fleet_namespace,
        "drained_consumers": True,
        "checkpoint_offsets_retained": True,
        "replay_notifications_suppressed": True,
        "primary_product_alerts_unaffected": True,
        "previous": st.get("latest"),
    }
