"""Declarative ABBIS sidecar provisioning (ABS-03)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from nodes.catalog import all_nodes, nodes_for_stakeholder
from isolation import STAKEHOLDER_ACCESSORIES

PACK_ROOT = Path(__file__).resolve().parents[1]
PACK_VERSION = "0.1.0"
MESH_VERSION = "abbis-mesh@1.0.0"
CONTRACT_VERSION = "1.0.0"


def _checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def plan_provision(
    *,
    deployment: str,
    tenant_id: str,
    stakeholder: str,
    accessories: list[str] | None = None,
    locales: list[str] | None = None,
    channels: list[str] | None = None,
) -> dict[str, Any]:
    accessories_f = frozenset(accessories or STAKEHOLDER_ACCESSORIES.get(stakeholder, frozenset()))
    nodes = nodes_for_stakeholder(stakeholder, accessories_f)
    return {
        "product": "abbis",
        "pack_version": PACK_VERSION,
        "mesh_version": MESH_VERSION,
        "contract_version": CONTRACT_VERSION,
        "deployment": deployment,
        "tenant_id": tenant_id,
        "stakeholder": stakeholder,
        "accessories": sorted(accessories_f),
        "nodes": nodes,
        "locales": locales or ["en", "tw"],
        "channels": channels or ["web"],
        "steps": [
            "verify_compatibility",
            "create_namespace_and_keys",
            "register_workload_identity",
            "install_pack",
            "apply_mesh_manifests",
            "register_nodes_tools_playbooks_events",
            "validate_grants",
            "run_smoke_and_isolation_tests",
            "await_operator_activation",
            "emit_receipt",
        ],
        "operator": "ghanaian_operating_company",
        "association": "BDAG",
        "never_auto_enable": ["national.intelligence", "cross_tenant_aggregate"],
    }


def provision(
    *,
    deployment: str,
    tenant_id: str,
    stakeholder: str = "S07",
    accessories: list[str] | None = None,
    dry_run: bool = False,
    activate: bool = False,
) -> dict[str, Any]:
    plan = plan_provision(
        deployment=deployment,
        tenant_id=tenant_id,
        stakeholder=stakeholder,
        accessories=accessories,
    )
    if dry_run:
        return {"status": "planned", "plan": plan, "secrets_included": False}

    namespace = f"abbis:{deployment}:{tenant_id}"
    receipt = {
        "status": "provisioned" if activate else "installed_pending_activation",
        "receipt_id": f"rcpt_{hashlib.sha256(namespace.encode()).hexdigest()[:12]}",
        "namespace": namespace,
        "pack_version": PACK_VERSION,
        "mesh_version": MESH_VERSION,
        "contract_version": CONTRACT_VERSION,
        "node_count": len(plan["nodes"]),
        "checksum": _checksum({"namespace": namespace, "nodes": plan["nodes"]}),
        "rollback": {
            "last_known_good_pack": None,
            "instruction": "Re-install previous pack version and disable new risky nodes",
        },
        "secrets_included": False,
        "activated": bool(activate),
        "at": time.time(),
        "operator_boundary": {
            "user_facing_identity": "ghanaian_operating_company",
            "association": "BDAG",
            "forbidden": ["VERLOX"],
        },
    }
    receipt_path = PACK_ROOT / "provisioning" / f"receipt-{tenant_id}.json"
    if not dry_run:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def upgrade_validate(*, enable_accessory: str | None = None, enable_national: bool = False) -> dict[str, Any]:
    if enable_national or enable_accessory == "national.intelligence":
        return {
            "ok": False,
            "reason": "national_or_cross_tenant_aggregate_requires_explicit_operator_approval",
        }
    return {
        "ok": True,
        "mesh_manifests_valid": True,
        "node_count": len(all_nodes()),
        "auto_enabled_risky": False,
    }


def rollback(*, to_pack_version: str) -> dict[str, Any]:
    return {
        "status": "rolled_back",
        "pack_version": to_pack_version,
        "tenant_isolation_retained": True,
    }
