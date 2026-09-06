"""Property-line entitlement and record-only-safe API metering."""

from __future__ import annotations

import json
import os
import uuid
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

_TIERS = {"community": 0, "local": 1, "email": 2, "priority": 3, "full": 4, "pro": 4}


def _grandfather_path() -> Path:
    root = Path(os.environ.get("KEPRIX_HOME", str(Path.home() / ".keprix"))) / "billing"
    root.mkdir(parents=True, exist_ok=True)
    return root / "property-grandfathering.json"


def _grandfathered(workspace_id: str) -> bool:
    try:
        rows = json.loads(_grandfather_path().read_text(encoding="utf-8"))
        return workspace_id in rows if isinstance(rows, list) else bool(rows.get(workspace_id))
    except (OSError, json.JSONDecodeError):
        return False


def workspace_property_entitlement(workspace_id: str) -> dict[str, Any]:
    from keprix.billing.grandfathering import workspace_has_feature_grandfather
    grandfathered = _grandfathered(workspace_id) or workspace_has_feature_grandfather(workspace_id, "property")
    if os.environ.get("KEPRIX_BILLING_ENABLED", "").lower() not in {"1", "true", "yes", "on"}:
        return {"workspace_id": workspace_id, "current_tier": "local", "required_tier": "full", "included": True, "grandfathered": grandfathered, "billing_enabled": False}
    current = os.environ.get("KEPRIX_PROPERTY_CURRENT_TIER", "community").strip().lower()
    required = os.environ.get("KEPRIX_PROPERTY_REQUIRED_TIER", "full").strip().lower()
    included = grandfathered or _TIERS.get(current, 0) >= _TIERS.get(required, 4)
    return {"workspace_id": workspace_id, "current_tier": current, "required_tier": required, "included": included, "grandfathered": grandfathered, "billing_enabled": True}


def require_property_entitlement(workspace_id: str) -> dict[str, Any]:
    status = workspace_property_entitlement(workspace_id)
    if not status["included"]:
        raise HTTPException(status_code=402, detail={"error": "Property line requires an eligible plan", "code": "property_entitlement_required", "required_tier": status["required_tier"], "current_tier": status["current_tier"]})
    return status


def meter_property_api_call(*, workspace_id: str, endpoint: str, cost: float = 1.0, connection=None, key_id: str = "", uprn: str = "", postcode: str = "", idempotency_key: str = "") -> dict[str, Any]:
    """Increment usage after success; metering failures are intentionally non-fatal."""
    try:
        if connection is None:
            from keprix.property_data.refresh import _connection
            connection = _connection()
        from keprix.property_data.schema import ensure_schema
        ensure_schema(connection)
        now = datetime.now(timezone.utc).isoformat()
        row_id = uuid.uuid4().hex
        if idempotency_key:
            existing = connection.execute(
                "SELECT id,cost_tokens FROM property_api_calls WHERE workspace_id=? AND idempotency_key=?",
                (workspace_id, idempotency_key),
            ).fetchone()
            if existing:
                return {"ok": True, "cost": float(existing[1] or 0), "idempotent": True, "id": existing[0]}
        connection.execute("INSERT INTO property_api_calls (id,workspace_id,key_id,endpoint,uprn,postcode,cost_tokens,called_at,idempotency_key) VALUES (?,?,?,?,?,?,?,?,?)", (row_id, workspace_id, key_id, endpoint, uprn, postcode, float(cost), now, idempotency_key))
        connection.commit()
        try:
            from keprix.billing.wallet.store import get_ai_credit_store
            store = get_ai_credit_store()
            marker = idempotency_key or row_id
            if not store.has_ledger_marker(workspace_id, marker):
                credits = max(1, int(math.ceil(float(cost))))
                store.append_entry(
                    workspace_id=workspace_id,
                    entry_type="debit",
                    credits=-credits,
                    channel="property_api",
                    run_id=row_id,
                    note=f"Property API usage: {endpoint}",
                    metadata={"idempotency_key": marker, "property_api_call_id": row_id, "cost_tokens": float(cost)},
                    apply_to_balance=False,
                    apply_to_included=False,
                )
                store.add_daily_usage(workspace_id, credits)
        except Exception:
            pass
        return {"ok": True, "cost": float(cost), "idempotent": False, "id": row_id}
    except Exception as exc:  # billing must never take down a successful read
        return {"ok": False, "error": str(exc)}
