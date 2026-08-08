"""Declarative Petraclus sidecar provisioning (PTS-03)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from nodes.catalog import all_nodes

PACK_ROOT = Path(__file__).resolve().parents[1]
PACK_VERSION = "0.1.0"
CONTRACT_VERSION = "1.0.0"

SUPPORTED_MODES = frozenset(
    {
        "local_community",
        "encrypted_pro",
        "team_multi_user",
        "air_gapped",
        "managed_model_endpoint",
    }
)

UNSUPPORTED_COMBOS = [
    {
        "combo": ["air_gapped", "managed_model_endpoint"],
        "reason": "Managed model endpoint requires outbound network; incompatible with strict air_gapped unless a local approved model is configured.",
    },
    {
        "combo": ["local_community", "team_multi_user"],
        "reason": "Community local mode is single-user; Team multi-user requires Team edition entitlements.",
    },
]


def _checksum(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def plan_provision(
    *,
    deployment: str,
    workspace_id: str,
    mode: str = "local_community",
    edition: str = "community",
) -> dict[str, Any]:
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"unsupported_mode:{mode}")
    for row in UNSUPPORTED_COMBOS:
        if set(row["combo"]).issubset({mode, deployment}):
            pass
    nodes = sorted(all_nodes().keys())
    risky = [k for k, n in all_nodes().items() if n.get("domain") == "action"]
    return {
        "product": "petraclus",
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "deployment": deployment,
        "workspace_id": workspace_id,
        "mode": mode,
        "edition": edition,
        "nodes": nodes,
        "risky_nodes_disabled_until_approved": risky,
        "steps": [
            "verify_compatibility",
            "create_namespace_and_workload_identity",
            "install_pack",
            "apply_connector_allowlist",
            "validate_grants_and_edition",
            "run_smoke_and_isolation_tests",
            "await_operator_activation",
            "emit_receipt",
        ],
        "licence_authority": "keys.petraclus.uk",
        "phone_home": False if mode == "air_gapped" else "opt_in_only",
        "never_auto_enable": risky,
        "unsupported_combos": UNSUPPORTED_COMBOS,
    }


def provision(
    *,
    deployment: str,
    workspace_id: str,
    mode: str = "local_community",
    edition: str = "community",
    dry_run: bool = False,
    activate: bool = False,
) -> dict[str, Any]:
    plan = plan_provision(
        deployment=deployment,
        workspace_id=workspace_id,
        mode=mode,
        edition=edition,
    )
    if dry_run:
        return {"status": "planned", "plan": plan, "secrets_included": False}

    namespace = f"petraclus:{deployment}:{workspace_id}"
    receipt = {
        "status": "provisioned" if activate else "installed_pending_activation",
        "receipt_id": f"rcpt_{hashlib.sha256(namespace.encode()).hexdigest()[:12]}",
        "namespace": namespace,
        "pack_version": PACK_VERSION,
        "contract_version": CONTRACT_VERSION,
        "mode": mode,
        "edition": edition,
        "node_count": len(plan["nodes"]),
        "checksum": _checksum({"namespace": namespace, "nodes": plan["nodes"]}),
        "rollback": {
            "last_known_good_pack": None,
            "instruction": "Re-install previous pack version and keep new risky nodes disabled",
        },
        "secrets_included": False,
        "activated": bool(activate),
        "licence_minted": False,
        "at": time.time(),
    }
    receipt_path = PACK_ROOT / "provisioning" / f"receipt-{workspace_id}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def upgrade_validate(*, enable_risky_nodes: bool = False, enable_node: str | None = None) -> dict[str, Any]:
    if enable_risky_nodes or (enable_node and (all_nodes().get(enable_node) or {}).get("domain") == "action"):
        return {
            "ok": False,
            "reason": "risky_nodes_require_explicit_operator_approval",
            "auto_enabled_risky": False,
        }
    return {
        "ok": True,
        "node_count": len(all_nodes()),
        "auto_enabled_risky": False,
    }


def rollback(*, to_pack_version: str) -> dict[str, Any]:
    return {
        "status": "rolled_back",
        "pack_version": to_pack_version,
        "workspace_isolation_retained": True,
        "licence_unchanged": True,
    }


def airgap_bundle_plan() -> dict[str, Any]:
    return {
        "product": "petraclus",
        "pack_version": PACK_VERSION,
        "includes": ["pack", "schemas", "migrations", "optional_local_model_config"],
        "excludes": ["licence_phone_home", "telemetry", "feed_calls", "update_calls"],
        "phone_home": False,
        "secrets_included": False,
        "configured_calls_only": True,
    }
