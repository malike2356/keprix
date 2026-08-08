"""Saved versioned ICP definitions (prompt 452)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import gate_or_approve
from keprix.crm.store import _utcnow


def _dumps_list(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, str):
        return value
    return json.dumps(list(value), ensure_ascii=False)


def _loads_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value or "[]")
            return list(parsed) if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _normalize_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    out = dict(row)
    for key in ("include_rules", "exclude_rules", "geography", "keywords", "sic_codes"):
        out[key] = _loads_list(out.get(key))
    out["active"] = bool(out.get("active"))
    return out


def _ensure(store: Any) -> None:
    ensure_nice_schema(store)


def list_icps(store: Any, workspace_id: str, *, name: str | None = None) -> list[dict[str, Any]]:
    _ensure(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        if name:
            rows = store._fetchall(
                "SELECT * FROM crm_icp_definitions WHERE workspace_id = ? AND name = ? "
                "ORDER BY name ASC, version DESC",
                (ws, name),
            )
        else:
            rows = store._fetchall(
                "SELECT * FROM crm_icp_definitions WHERE workspace_id = ? "
                "ORDER BY name ASC, version DESC",
                (ws,),
            )
    return [r for r in (_normalize_row(x) for x in rows) if r]


def get_icp(store: Any, workspace_id: str, icp_id: str) -> dict[str, Any] | None:
    _ensure(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        row = store._fetchone(
            "SELECT * FROM crm_icp_definitions WHERE workspace_id = ? AND id = ?",
            (ws, icp_id),
        )
    return _normalize_row(row)


def get_active_icp(store: Any, workspace_id: str, *, pack: str | None = None) -> dict[str, Any] | None:
    _ensure(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        if pack:
            row = store._fetchone(
                "SELECT * FROM crm_icp_definitions WHERE workspace_id = ? AND active = 1 "
                "AND pack = ? ORDER BY updated_at DESC LIMIT 1",
                (ws, pack),
            )
        else:
            row = store._fetchone(
                "SELECT * FROM crm_icp_definitions WHERE workspace_id = ? AND active = 1 "
                "ORDER BY updated_at DESC LIMIT 1",
                (ws,),
            )
    return _normalize_row(row)


def create_icp(
    store: Any,
    workspace_id: str,
    *,
    name: str,
    pack: str = "generic",
    include_rules: list[Any] | None = None,
    exclude_rules: list[Any] | None = None,
    geography: list[Any] | None = None,
    size_band: str | None = None,
    keywords: list[Any] | None = None,
    sic_codes: list[Any] | None = None,
    notes: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Create version 1 of a named ICP (inactive until Soft Wall activate)."""
    _ensure(store)
    ws = store._require_workspace(workspace_id)
    name = str(name or "").strip()
    if not name:
        raise ValueError("name_required")
    now = _utcnow()
    row_id = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_icp_definitions (
                id, workspace_id, name, version, pack,
                include_rules, exclude_rules, geography, size_band,
                keywords, sic_codes, notes, active, parent_id,
                actor_type, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?)
            """,
            (
                row_id,
                ws,
                name,
                pack or "generic",
                _dumps_list(include_rules or []),
                _dumps_list(exclude_rules or []),
                _dumps_list(geography or []),
                size_band,
                _dumps_list(keywords or []),
                _dumps_list(sic_codes or []),
                notes,
                actor_type,
                actor_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return get_icp(store, ws, row_id) or {"id": row_id}


def revise_icp(
    store: Any,
    workspace_id: str,
    icp_id: str,
    *,
    include_rules: list[Any] | None = None,
    exclude_rules: list[Any] | None = None,
    geography: list[Any] | None = None,
    size_band: str | None = None,
    keywords: list[Any] | None = None,
    sic_codes: list[Any] | None = None,
    notes: str | None = None,
    pack: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Immutable edit: clone as version N+1 (inactive)."""
    parent = get_icp(store, workspace_id, icp_id)
    if not parent:
        raise LookupError("icp_not_found")
    ws = store._require_workspace(workspace_id)
    next_version = int(parent.get("version") or 1) + 1
    # If another draft already exists at N+1 for same name, bump further.
    existing = list_icps(store, ws, name=str(parent["name"]))
    max_v = max(int(r.get("version") or 1) for r in existing) if existing else 1
    next_version = max(next_version, max_v + 1)
    now = _utcnow()
    row_id = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_icp_definitions (
                id, workspace_id, name, version, pack,
                include_rules, exclude_rules, geography, size_band,
                keywords, sic_codes, notes, active, parent_id,
                actor_type, actor_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                ws,
                parent["name"],
                next_version,
                pack or parent.get("pack") or "generic",
                _dumps_list(include_rules if include_rules is not None else parent.get("include_rules")),
                _dumps_list(exclude_rules if exclude_rules is not None else parent.get("exclude_rules")),
                _dumps_list(geography if geography is not None else parent.get("geography")),
                size_band if size_band is not None else parent.get("size_band"),
                _dumps_list(keywords if keywords is not None else parent.get("keywords")),
                _dumps_list(sic_codes if sic_codes is not None else parent.get("sic_codes")),
                notes if notes is not None else parent.get("notes"),
                parent["id"],
                actor_type,
                actor_id,
                now,
                now,
            ),
        )
        store._conn.commit()
    return get_icp(store, ws, row_id) or {"id": row_id}


def activate_icp(
    store: Any,
    workspace_id: str,
    icp_id: str,
    *,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    """Soft Wall activate one ICP version; deactivates siblings of the same name."""
    row = get_icp(store, workspace_id, icp_id)
    if not row:
        raise LookupError("icp_not_found")
    gate = gate_or_approve(
        workspace_id,
        kind="icp_activate",
        subject=f"Activate ICP {row['name']} v{row['version']}",
        payload={"icp_id": icp_id, "name": row["name"], "version": row["version"], "pack": row.get("pack")},
        object_type="icp",
        object_id=icp_id,
        actor_id=actor_id,
        force=force,
        approval_id=approval_id,
    )
    if gate.get("blocked"):
        return {"ok": False, "blocked": True, "approval": gate.get("approval"), "error_code": gate.get("error_code")}

    ws = store._require_workspace(workspace_id)
    now = _utcnow()
    with store._lock:
        store._conn.execute(
            "UPDATE crm_icp_definitions SET active = 0, updated_at = ? "
            "WHERE workspace_id = ? AND name = ?",
            (now, ws, row["name"]),
        )
        store._conn.execute(
            "UPDATE crm_icp_definitions SET active = 1, updated_at = ? "
            "WHERE workspace_id = ? AND id = ?",
            (now, ws, icp_id),
        )
        store._conn.commit()
    activated = get_icp(store, ws, icp_id)
    return {"ok": True, "blocked": False, "icp": activated}


def diff_icp_versions(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Rule-level diff between two ICP rows."""
    fields = (
        "pack",
        "include_rules",
        "exclude_rules",
        "geography",
        "size_band",
        "keywords",
        "sic_codes",
        "notes",
        "active",
        "version",
    )
    changes: list[dict[str, Any]] = []
    for field in fields:
        left = a.get(field)
        right = b.get(field)
        if left != right:
            changes.append({"field": field, "from": left, "to": right})
    return {
        "left": {"id": a.get("id"), "name": a.get("name"), "version": a.get("version")},
        "right": {"id": b.get("id"), "name": b.get("name"), "version": b.get("version")},
        "changes": changes,
        "changed": bool(changes),
    }


def _rule_field(rule: Any) -> tuple[str, str]:
    if isinstance(rule, dict):
        field = str(rule.get("field") or rule.get("type") or "keyword").lower()
        value = str(rule.get("value") or rule.get("pattern") or "").strip().lower()
        return field, value
    return "keyword", str(rule or "").strip().lower()


def candidate_matches_exclude(row: dict[str, Any], exclude_rules: list[Any]) -> bool:
    """True when a lead/contact should be removed by ICP exclusions."""
    if not exclude_rules:
        return False
    hay = {
        "domain": str(row.get("domain") or "").lower(),
        "company": str(row.get("company_name") or row.get("name") or "").lower(),
        "email": "",
        "sic": str(row.get("company_number") or "").lower(),
        "geo": str((row.get("addresses") or row.get("geo") or "")).lower(),
        "keyword": " ".join(
            str(x)
            for x in (
                row.get("name"),
                row.get("company_name"),
                row.get("domain"),
                " ".join(str(t) for t in (row.get("tags") or [])),
            )
            if x
        ).lower(),
    }
    emails = row.get("emails") or []
    for item in emails:
        if isinstance(item, dict):
            hay["email"] = str(item.get("address") or "").lower()
        else:
            hay["email"] = str(item or "").lower()
        if "@" in hay["email"]:
            hay["domain"] = hay["domain"] or hay["email"].split("@", 1)[1]

    for rule in exclude_rules:
        field, value = _rule_field(rule)
        if not value:
            continue
        target = hay.get(field) or hay["keyword"]
        if value in target:
            return True
    return False


def apply_icp_exclusions(
    store: Any,
    workspace_id: str,
    members: list[dict[str, Any]],
    *,
    icp_id: str | None = None,
    icp_version: int | None = None,
) -> dict[str, Any]:
    """Filter enroll/discovery candidates against ICP exclude rules."""
    icp = None
    if icp_id:
        icp = get_icp(store, workspace_id, icp_id)
    if not icp:
        icp = get_active_icp(store, workspace_id)
    if not icp:
        return {"kept": members, "excluded": [], "icp": None}
    if icp_version is not None and int(icp.get("version") or 0) != int(icp_version):
        # Prefer exact version when provided
        for row in list_icps(store, workspace_id, name=str(icp.get("name") or "")):
            if int(row.get("version") or 0) == int(icp_version):
                icp = row
                break

    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    rules = list(icp.get("exclude_rules") or [])
    for mem in members:
        if candidate_matches_exclude(mem, rules):
            excluded.append({**mem, "reason": "icp_exclude", "icp_id": icp["id"], "icp_version": icp.get("version")})
        else:
            kept.append(mem)
    return {"kept": kept, "excluded": excluded, "icp": icp}


def stamp_entity_icp(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    icp_id: str,
    icp_version: int,
) -> None:
    """Best-effort stamp icp_id/version on list/lead/job after nice schema columns exist."""
    _ensure(store)
    table = {
        "lead": "crm_leads",
        "list": "crm_lists",
        "discovery_job": "crm_discovery_jobs",
        "contact": "crm_contacts",
        "deal": "crm_deals",
        "account": "crm_accounts",
    }.get(entity_type)
    if not table:
        return
    ws = store._require_workspace(workspace_id)
    with store._lock:
        cols = {r[1] for r in store._conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "icp_id" not in cols:
            return
        store._conn.execute(
            f"UPDATE {table} SET icp_id = ?, icp_version = ? WHERE id = ? AND workspace_id = ?",
            (icp_id, int(icp_version), entity_id, ws),
        )
        store._conn.commit()
