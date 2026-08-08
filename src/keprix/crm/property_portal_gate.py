"""Property portal checklist acknowledgment helpers (prompt 464)."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve
from keprix.discovery.adapters.property_portals import LEGAL_CHECKLIST, PROPERTY_PORTAL_FLAG, property_portals_enabled

CHECKLIST_VERSION = "property-portal-2026.1"
_KILL = False


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def kill_switch_engaged() -> bool:
    return _KILL or os.environ.get("KEPRIX_PROPERTY_PORTAL_KILL", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def set_kill_switch(engaged: bool) -> dict[str, Any]:
    global _KILL
    _KILL = bool(engaged)
    return {"ok": True, "kill_switch": _KILL}


def latest_ack(store: Any, workspace_id: str) -> dict[str, Any] | None:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    return store._fetchone(
        """
        SELECT * FROM crm_portal_checklist_acks
        WHERE workspace_id = ?
        ORDER BY acknowledged_at DESC
        LIMIT 1
        """,
        (ws,),
    )


def acknowledge_checklist(
    store: Any,
    workspace_id: str,
    *,
    acknowledged_by: str,
    notes: str | None = None,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    gate = gate_or_approve(
        ws,
        kind="property_portal_checklist",
        subject="Acknowledge property portal legal checklist",
        payload={"checklist_version": CHECKLIST_VERSION, "docs": LEGAL_CHECKLIST},
        object_type="property_portal",
        object_id=CHECKLIST_VERSION,
        actor_id=actor_id or acknowledged_by,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval")}
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_portal_checklist_acks (
                id, workspace_id, checklist_version, acknowledged_by, acknowledged_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rid, ws, CHECKLIST_VERSION, acknowledged_by, _utcnow(), notes),
        )
        store._conn.commit()
    return {"ok": True, "ack": latest_ack(store, ws)}


def portal_gate_status(store: Any, workspace_id: str) -> dict[str, Any]:
    ack = latest_ack(store, workspace_id)
    return {
        "flag": PROPERTY_PORTAL_FLAG,
        "flag_enabled": property_portals_enabled(workspace_id),
        "checklist": LEGAL_CHECKLIST,
        "checklist_version": CHECKLIST_VERSION,
        "acknowledged": bool(ack),
        "ack": ack,
        "kill_switch": kill_switch_engaged(),
        "can_enable_jobs": bool(ack) and property_portals_enabled(workspace_id) and not kill_switch_engaged(),
        "configure_path": "/crm/settings#connections",
        "note": (
            "Not legal advice. Prefer licensed/API feeds. HTML scrape remains experimental and off by default."
        ),
    }


def assert_portal_job_allowed(store: Any, workspace_id: str) -> dict[str, Any]:
    status = portal_gate_status(store, workspace_id)
    if kill_switch_engaged():
        return {"ok": False, "error": "kill_switch", "status": status}
    if not status["flag_enabled"]:
        return {"ok": False, "error": "flag_off", "status": status}
    if not status["acknowledged"]:
        return {"ok": False, "error": "checklist_required", "status": status}
    return {"ok": True, "status": status}
