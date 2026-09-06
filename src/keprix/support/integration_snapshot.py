"""Read-only workspace integration status aggregation."""

from __future__ import annotations

from typing import Any

from keprix.crm.connections import connections_status
from keprix.crm.store import CrmStore, get_crm_store


def workspace_integration_snapshot(workspace_id: str, *, store: CrmStore | None = None) -> dict[str, Any]:
    """Return safe status data without reconnecting or probing remote services."""
    store = store or get_crm_store()
    status = connections_status(store, workspace_id)
    names = ("telegram", "email", "google", "calendar", "whatsapp", "linkedin", "meta", "x", "workers", "domains")
    groups = status.get("groups") or {}
    items: list[dict[str, Any]] = []
    for name in names:
        group = groups.get(name) or groups.get("messaging" if name in {"telegram", "whatsapp"} else name) or []
        configured = bool(group) and any(bool(row.get("configured")) for row in group)
        last_seen = max((row.get("updated_at") for row in group if row.get("updated_at")), default=None)
        items.append({"integration": name, "status": "connected" if configured else "disconnected", "last_seen": last_seen, "details": group})
    return {"workspace_id": workspace_id, "items": items, "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
