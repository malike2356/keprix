"""Operator readiness snapshot for product packs (prompt 643).

Health connectivity alone is not CRUD readiness. This module aggregates pack
honesty, Soft Wall backlog, event lag, last canary receipts, circuit, and
emergency controls for operator UI and docs.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from keprix.product_sidecar.state import (
    get_approval_store,
    get_circuit,
    get_event_store,
    get_kill_switches,
    get_receipt_store,
)
from keprix.product_sidecar.registry import get_product_pack_registry


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(ts)))


def _evidence_mtime() -> float | None:
    try:
        root = Path(__file__).resolve().parents[3]
        evidence = root / "docs" / "architecture" / "propreneur-e2e-evidence.v1.json"
        if evidence.is_file():
            return evidence.stat().st_mtime
    except OSError:
        return None
    return None


def build_product_readiness(product_key: str) -> dict[str, Any]:
    """Machine-readable readiness for operator surfaces (not marketing CRUD claims)."""
    registry = get_product_pack_registry()
    pack = registry.require(product_key)
    kills = get_kill_switches()
    counts = pack.node_status_counts()
    live = int(counts.get("live", 0) or 0)
    approval_required = int(counts.get("approval_required", 0) or 0)
    not_configured = int(counts.get("not_configured", 0) or 0)
    degraded = int(counts.get("degraded", 0) or 0)
    forbidden = int(counts.get("intentionally_forbidden", 0) or 0)
    proposal_only = int(counts.get("proposal_only", 0) or 0)

    honesty = "ok"
    if product_key == "propreneur" and (not_configured or degraded):
        honesty = "partial_fail_closed"
    if product_key == "propreneur" and live == 0 and approval_required == 0:
        honesty = "fail_closed_remediation"

    pending = get_approval_store().count_pending(product=product_key)
    receipts = get_receipt_store().list_for_product(product_key, limit=200)
    last_read = next((r for r in receipts if str(r.get("method") or "").upper() == "GET"), None)
    last_write = next(
        (r for r in receipts if str(r.get("method") or "").upper() in {"POST", "PATCH", "PUT", "DELETE"}),
        None,
    )

    events = get_event_store().list_for_product(product_key)
    unacked = [e for e in events if not e.get("acked")]
    newest = max((float(e.get("ingested_at") or e.get("created_at") or 0) for e in events), default=0.0)
    oldest_unacked = min(
        (float(e.get("ingested_at") or e.get("created_at") or 0) for e in unacked if e.get("ingested_at") or e.get("created_at")),
        default=0.0,
    )
    now = time.time()
    event_lag_seconds = None
    if oldest_unacked:
        event_lag_seconds = max(0.0, now - oldest_unacked)

    evidence_ts = _evidence_mtime()
    connector = dict(pack.connector or {})
    base_url = str(connector.get("base_url") or connector.get("base_url_env") or "")

    crud_ready = live > 0 and not_configured == 0 and degraded == 0
    return {
        "product": product_key,
        "engine_connectivity": "ok" if pack.enabled else "disabled",
        "note": (
            "HTTP health/connectivity is not CRUD readiness. "
            "Safe full CRUD means domain API access via ProductApiConnector and Soft Wall; "
            "not raw database access, hard delete, or generic proxy."
        ),
        "pack_readiness": {
            "enabled": pack.enabled,
            "pack_version": pack.version,
            "contract_version": pack.contract_version,
            "checksum": pack.checksum,
            "wrapper_of": pack.wrapper_of,
            "crud_complete": crud_ready,
            "capability_honesty": honesty,
        },
        "node_counts": counts,
        "operation_counts": {
            "live": live,
            "approval_required": approval_required,
            "proposal_only": proposal_only,
            "not_configured": not_configured,
            "degraded": degraded,
            "intentionally_forbidden": forbidden,
            "executable": live + approval_required,
        },
        "actor_and_tenant_binding": {
            "model": "TrustedExecutionContext",
            "headers": [
                "X-Keprix-Trusted-Workspace-Id",
                "X-Keprix-Trusted-Actor-Id",
                "X-Keprix-Trusted-Actor-Type",
                "X-Keprix-Trusted-Product",
                "Authorization (grant bearer; server-side only)",
                "Host (tenant domain for Propreneur tenancy)",
            ],
            "model_cannot_override_identity": True,
            "grants": "Delegated Aiva grant scopes + pack node required_grants",
        },
        "callback_health": {
            "connector_base_url_env": connector.get("base_url_env") or "PROPRENEUR_PRODUCT_API_URL",
            "connector_configured": bool(base_url) or product_key != "propreneur",
            "host_allowlist": list(connector.get("host_allowlist") or []),
            "guidance": (
                "Diagnose failed callbacks with correlation_id, Soft Wall approval_id, "
                "circuit state, grant revoke/expiry, and If-Match version conflicts."
            ),
        },
        "pending_approvals": {
            "count": pending,
            "sample": get_approval_store().list_pending(product=product_key, limit=5),
        },
        "event_lag": {
            "unacked_count": len(unacked),
            "lag_seconds": event_lag_seconds,
            "newest_ingested_at": _iso(newest or None),
        },
        "last_successful_canary": {
            "evidence_file_mtime": _iso(evidence_ts),
            "last_read_receipt": (
                {
                    "node": last_read.get("node_key"),
                    "at": _iso(last_read.get("created_at")),
                    "receipt_id": last_read.get("receipt_id"),
                }
                if last_read
                else None
            ),
            "last_write_receipt": (
                {
                    "node": last_write.get("node_key"),
                    "at": _iso(last_write.get("created_at")),
                    "receipt_id": last_write.get("receipt_id"),
                }
                if last_write
                else None
            ),
        },
        "circuit": get_circuit().state(),
        "emergency_controls": {
            "force_carina": kills.force_carina,
            "outbound_kill": kills.outbound_kill,
            "pack_enabled": pack.enabled,
            "admin_route": f"/v1/products/{product_key}/admin/kill",
        },
        "source_of_truth": "Propreneur Laravel domain services via /api/aiva/v1 (not Keprix local CRM)",
    }
