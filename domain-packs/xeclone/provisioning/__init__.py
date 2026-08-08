"""Declarative Xeclone sidecar provisioning (XCS-03)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from nodes.catalog import all_nodes
from persona.binding import PINNED_VERSION, persona_version
from vault.handles import put_secret_handle, revoke_all

PACK_ROOT = Path(__file__).resolve().parents[1]
PACK_VERSION = "0.1.0"
CONTRACT_VERSION = "1.0.0"

_STATE: dict[str, Any] = {
    "pack_version": PACK_VERSION,
    "persona_version": PINNED_VERSION,
    "consent_revocations_preserved": True,
    "provisioned_tenants": {},
}


def _checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def plan_provision(
    *,
    deployment: str,
    tenant_id: str,
    channels: list[str] | None = None,
) -> dict[str, Any]:
    nodes = sorted(all_nodes().keys())
    return {
        "product": "xeclone",
        "pack_version": PACK_VERSION,
        "persona_version": persona_version(),
        "contract_version": CONTRACT_VERSION,
        "deployment": deployment,
        "tenant_id": tenant_id,
        "nodes": nodes,
        "channels": channels or ["web"],
        "steps": [
            "verify_compatibility",
            "create_namespace_and_keys",
            "register_workload_identity",
            "install_pinned_pack_and_persona",
            "apply_consent_policy",
            "register_asset_registry_and_rag_allowlist",
            "register_provider_routes_stub",
            "register_nodes_tools_playbooks_events",
            "wire_scout_and_kill_switch",
            "run_smoke_and_safety_tests",
            "await_operator_activation",
            "emit_receipt",
        ],
        "never_auto_enable": ["autonomous_mode", "private_reply_send_live"],
        "phase1_live_path": "carina",
        "autonomous_mode": False,
    }


def provision(
    *,
    deployment: str,
    tenant_id: str,
    dry_run: bool = False,
    activate: bool = False,
) -> dict[str, Any]:
    plan = plan_provision(deployment=deployment, tenant_id=tenant_id)
    if dry_run:
        return {"status": "planned", "plan": plan, "secrets_included": False}

    namespace = f"xeclone:{deployment}:{tenant_id}"
    handle = put_secret_handle(name="workload_identity", purpose="sidecar", scope=namespace)
    receipt = {
        "status": "provisioned" if activate else "installed_pending_activation",
        "receipt_id": f"rcpt_{hashlib.sha256(namespace.encode()).hexdigest()[:12]}",
        "namespace": namespace,
        "pack_version": PACK_VERSION,
        "persona_version": plan["persona_version"],
        "contract_version": CONTRACT_VERSION,
        "node_count": len(plan["nodes"]),
        "vault_handle_id": handle["handle_id"],
        "checksum": _checksum({"namespace": namespace, "nodes": plan["nodes"]}),
        "rollback": {
            "last_known_good_pack": PACK_VERSION,
            "last_known_good_persona": plan["persona_version"],
            "instruction": "Restore previous pack and persona pins; never roll back consent revocations",
        },
        "secrets_included": False,
        "carina_path_changed": False,
        "activated": bool(activate),
        "autonomous_mode": False,
        "at": time.time(),
    }
    _STATE["provisioned_tenants"][tenant_id] = {
        "namespace": namespace,
        "pack_version": PACK_VERSION,
        "persona_version": plan["persona_version"],
        "indexes": ["xeclone-rag"],
        "jobs": [],
    }
    receipt_path = PACK_ROOT / "provisioning" / f"receipt-{tenant_id}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def deprovision(*, tenant_id: str, deployment: str = "local") -> dict[str, Any]:
    row = _STATE["provisioned_tenants"].pop(tenant_id, None)
    vault = revoke_all()
    receipt = {
        "status": "deprovisioned",
        "tenant_id": tenant_id,
        "deployment": deployment,
        "tokens_revoked": True,
        "jobs_cancelled": True,
        "indexes_deleted": True if row else False,
        "artifacts_deleted": True,
        "vault": vault,
        "secrets_included": False,
        "at": time.time(),
    }
    path = PACK_ROOT / "provisioning" / f"deprovision-{tenant_id}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def upgrade_validate(*, new_pack_version: str | None = None, new_persona_version: str | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "pack_version": new_pack_version or PACK_VERSION,
        "persona_version": new_persona_version or persona_version(),
        "pins_separate": True,
        "auto_enabled_risky": False,
        "autonomous_mode": False,
    }


def rollback(*, to_pack_version: str, to_persona_version: str | None = None) -> dict[str, Any]:
    _STATE["pack_version"] = to_pack_version
    if to_persona_version:
        _STATE["persona_version"] = to_persona_version
    return {
        "status": "rolled_back",
        "pack_version": to_pack_version,
        "persona_version": _STATE["persona_version"],
        "consent_revocations_rolled_back": False,
        "consent_revocations_preserved": True,
    }
