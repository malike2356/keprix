"""Team assignment, SLA inbox, collision locks, comments (prompt 453)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.crm.nice_schema import ensure_nice_schema
from keprix.crm.soft_wall import PAYING_STAGES, gate_or_approve

ENTITY_TABLES = {
    "lead": "crm_leads",
    "contact": "crm_contacts",
    "account": "crm_accounts",
    "deal": "crm_deals",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _loads(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw or "[]")
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def ensure_team(store: Any, workspace_id: str, *, name: str, member_user_ids: list[str]) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    now = _iso(_utcnow())
    rid = str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_teams (id, workspace_id, name, member_user_ids, round_robin_cursor, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
            """,
            (rid, ws, name, json.dumps(list(member_user_ids)), now, now),
        )
        store._conn.commit()
    return get_team(store, ws, rid)  # type: ignore[return-value]


def get_team(store: Any, workspace_id: str, team_id: str) -> dict[str, Any] | None:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    row = store._fetchone(
        "SELECT * FROM crm_teams WHERE workspace_id = ? AND id = ?",
        (ws, team_id),
    )
    if not row:
        return None
    out = dict(row)
    out["member_user_ids"] = _loads(out.get("member_user_ids"))
    return out


def list_teams(store: Any, workspace_id: str) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    rows = store._fetchall(
        "SELECT * FROM crm_teams WHERE workspace_id = ? ORDER BY created_at ASC",
        (ws,),
    )
    out = []
    for row in rows:
        item = dict(row)
        item["member_user_ids"] = _loads(item.get("member_user_ids"))
        out.append(item)
    return out


def assign_owner(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    owner_user_id: str | None = None,
    team_id: str | None = None,
    mode: str = "manual",
    sla_hours: int | None = 24,
    actor_id: str | None = None,
    force: bool = False,
    approval_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    table = ENTITY_TABLES.get(entity_type)
    if not table:
        return {"ok": False, "error": "unsupported_entity"}
    row = store._fetchone(
        f"SELECT * FROM {table} WHERE workspace_id = ? AND id = ? AND deleted_at IS NULL",
        (ws, entity_id),
    )
    if not row:
        return {"ok": False, "error": "not_found"}

    if entity_type == "deal" and str(row.get("stage") or "") in PAYING_STAGES:
        gate = gate_or_approve(
            ws,
            kind="deal_reassign_paying",
            subject=f"Reassign paying deal {entity_id}",
            payload={"entity_type": entity_type, "entity_id": entity_id, "owner_user_id": owner_user_id},
            object_type="deal",
            object_id=entity_id,
            actor_id=actor_id,
            force=force,
            approval_id=approval_id,
        )
        if gate.get("blocked"):
            return {"ok": False, "blocked": True, "approval": gate.get("approval")}

    assigned = owner_user_id
    if mode == "round_robin":
        if not team_id:
            return {"ok": False, "error": "team_id_required"}
        assigned = next_round_robin(store, ws, team_id)
        if not assigned:
            return {"ok": False, "error": "team_empty"}
    elif mode == "claim":
        if row.get("owner_user_id"):
            return {"ok": False, "error": "already_assigned", "owner_user_id": row.get("owner_user_id")}
        assigned = owner_user_id or actor_id
        if not assigned:
            return {"ok": False, "error": "owner_required"}

    sla_due = None
    sla_state = "open"
    if sla_hours is not None:
        sla_due = _iso(_utcnow() + timedelta(hours=int(sla_hours)))
        sla_state = "due"

    with store._lock:
        store._conn.execute(
            f"""
            UPDATE {table}
            SET owner_user_id = ?, team_id = ?, sla_due_at = ?, sla_state = ?, updated_at = ?
            WHERE workspace_id = ? AND id = ?
            """,
            (assigned, team_id, sla_due, sla_state, _iso(_utcnow()), ws, entity_id),
        )
        store._conn.commit()
    refreshed = store._fetchone(
        f"SELECT * FROM {table} WHERE workspace_id = ? AND id = ?",
        (ws, entity_id),
    )
    return {"ok": True, "entity": refreshed, "mode": mode}


def next_round_robin(store: Any, workspace_id: str, team_id: str) -> str | None:
    team = get_team(store, workspace_id, team_id)
    if not team:
        return None
    members = [str(m) for m in team.get("member_user_ids") or [] if str(m).strip()]
    if not members:
        return None
    cursor = int(team.get("round_robin_cursor") or 0) % len(members)
    chosen = members[cursor]
    nxt = (cursor + 1) % len(members)
    with store._lock:
        store._conn.execute(
            "UPDATE crm_teams SET round_robin_cursor = ?, updated_at = ? WHERE id = ? AND workspace_id = ?",
            (nxt, _iso(_utcnow()), team_id, workspace_id),
        )
        store._conn.commit()
    return chosen


def acquire_lock(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    owner_user_id: str,
    ttl_seconds: int = 120,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    now = _utcnow()
    expires = now + timedelta(seconds=max(30, ttl_seconds))
    existing = store._fetchone(
        """
        SELECT * FROM crm_entity_locks
        WHERE workspace_id = ? AND entity_type = ? AND entity_id = ?
        """,
        (ws, entity_type, entity_id),
    )
    if existing:
        exp = existing.get("expires_at") or ""
        try:
            exp_dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        except ValueError:
            exp_dt = now
        if exp_dt > now and existing.get("owner_user_id") != owner_user_id:
            return {
                "ok": False,
                "conflict": True,
                "warning": "Record is locked by another operator",
                "lock": existing,
            }
    rid = existing["id"] if existing else str(uuid.uuid4())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_entity_locks (id, workspace_id, entity_type, entity_id, owner_user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id, entity_type, entity_id) DO UPDATE SET
                owner_user_id = excluded.owner_user_id,
                expires_at = excluded.expires_at
            """,
            (rid, ws, entity_type, entity_id, owner_user_id, _iso(expires), _iso(now)),
        )
        store._conn.commit()
    lock = store._fetchone(
        "SELECT * FROM crm_entity_locks WHERE workspace_id = ? AND entity_type = ? AND entity_id = ?",
        (ws, entity_type, entity_id),
    )
    return {"ok": True, "lock": lock}


def release_lock(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    with store._lock:
        if owner_user_id:
            store._conn.execute(
                """
                DELETE FROM crm_entity_locks
                WHERE workspace_id = ? AND entity_type = ? AND entity_id = ? AND owner_user_id = ?
                """,
                (ws, entity_type, entity_id, owner_user_id),
            )
        else:
            store._conn.execute(
                """
                DELETE FROM crm_entity_locks
                WHERE workspace_id = ? AND entity_type = ? AND entity_id = ?
                """,
                (ws, entity_type, entity_id),
            )
        store._conn.commit()
    return {"ok": True}


def add_comment(
    store: Any,
    workspace_id: str,
    *,
    entity_type: str,
    entity_id: str,
    body: str,
    mentions: list[str] | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    rid = str(uuid.uuid4())
    now = _iso(_utcnow())
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO crm_comments (
                id, workspace_id, entity_type, entity_id, body, mentions, actor_type, actor_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rid,
                ws,
                entity_type,
                entity_id,
                body,
                json.dumps(list(mentions or [])),
                actor_type,
                actor_id,
                now,
            ),
        )
        store._conn.commit()
    row = store._fetchone("SELECT * FROM crm_comments WHERE id = ?", (rid,))
    out = dict(row or {})
    out["mentions"] = _loads(out.get("mentions"))
    out["notification"] = {
        "channels": ["in_app"],
        "optional_telegram": True,
        "mentions": out["mentions"],
    }
    return out


def list_comments(store: Any, workspace_id: str, *, entity_type: str, entity_id: str) -> list[dict[str, Any]]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    rows = store._fetchall(
        """
        SELECT * FROM crm_comments
        WHERE workspace_id = ? AND entity_type = ? AND entity_id = ? AND deleted_at IS NULL
        ORDER BY created_at ASC
        """,
        (ws, entity_type, entity_id),
    )
    out = []
    for row in rows:
        item = dict(row)
        item["mentions"] = _loads(item.get("mentions"))
        out.append(item)
    return out


def sla_inbox(store: Any, workspace_id: str) -> dict[str, Any]:
    ensure_nice_schema(store)
    ws = store._require_workspace(workspace_id)
    now = _utcnow()
    today = now.date().isoformat()
    buckets = {"overdue": [], "due_today": [], "unassigned": []}
    for etype, table in ENTITY_TABLES.items():
        rows = store._fetchall(
            f"""
            SELECT *
            FROM {table}
            WHERE workspace_id = ? AND deleted_at IS NULL
            """,
            (ws,),
        )
        for row in rows:
            item = dict(row)
            item["entity_type"] = etype
            item["label"] = item.get("name") or item.get("display_name") or item["id"]
            if not item.get("owner_user_id"):
                buckets["unassigned"].append(item)
            due = item.get("sla_due_at")
            if not due:
                continue
            try:
                due_dt = datetime.fromisoformat(str(due).replace("Z", "+00:00"))
            except ValueError:
                continue
            if due_dt < now:
                item["sla_state"] = "overdue"
                buckets["overdue"].append(item)
            elif due_dt.date().isoformat() == today:
                buckets["due_today"].append(item)
    return {
        "overdue": buckets["overdue"],
        "due_today": buckets["due_today"],
        "unassigned": buckets["unassigned"],
        "counts": {k: len(v) for k, v in buckets.items()},
    }
