"""Workspace-scoped saved property searches and CRM handoff."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .refresh import _connection
from .schema import ensure_schema
from .scoring import score_signals


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_saved_search(workspace_id: str, name: str, criteria: dict[str, Any], *, run_schedule: str = "weekly", connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    item = (uuid.uuid4().hex, workspace_id, name.strip(), json.dumps(criteria), run_schedule.strip() or "weekly", 1, _now(), "")
    connection.execute("INSERT INTO property_saved_searches (id,workspace_id,name,criteria_json,run_schedule,active,created_at,last_run_at) VALUES (?,?,?,?,?,?,?,?)", item)
    connection.commit()
    return get_saved_search(item[0], workspace_id, connection=connection)


def get_saved_search(search_id: str, workspace_id: str, *, connection=None) -> dict[str, Any] | None:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT id,workspace_id,name,criteria_json,run_schedule,active,created_at,last_run_at FROM property_saved_searches WHERE id=? AND workspace_id=?", (search_id, workspace_id)).fetchone()
    if not row:
        return None
    return {"id": row[0], "workspace_id": row[1], "name": row[2], "criteria": json.loads(row[3] or "{}"), "run_schedule": row[4], "active": bool(row[5]), "created_at": row[6], "last_run_at": row[7], "matches": list_matches(search_id, workspace_id, connection=connection)}


def list_saved_searches(workspace_id: str, *, connection=None) -> list[dict[str, Any]]:
    connection = _connection(connection)
    ensure_schema(connection)
    ids = [row[0] for row in connection.execute("SELECT id FROM property_saved_searches WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,)).fetchall()]
    return [get_saved_search(item, workspace_id, connection=connection) for item in ids]


def list_matches(search_id: str, workspace_id: str, *, connection=None) -> list[dict[str, Any]]:
    connection = _connection(connection)
    rows = connection.execute("SELECT m.id,m.uprn,m.score,m.signals_json,m.status,m.found_at FROM property_saved_search_matches m JOIN property_saved_searches s ON s.id=m.saved_search_id WHERE m.saved_search_id=? AND s.workspace_id=? ORDER BY m.score DESC,m.uprn", (search_id, workspace_id)).fetchall()
    return [{"id": r[0], "uprn": r[1], "score": r[2], "signals": json.loads(r[3] or "{}"), "status": r[4], "found_at": r[5]} for r in rows]


def run_saved_search(search_id: str, workspace_id: str, *, connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    search = get_saved_search(search_id, workspace_id, connection=connection)
    if not search:
        return {"status": "not_found", "matches": []}
    criteria = search["criteria"]
    min_score = max(0.0, min(1.0, float(criteria.get("min_score", 0))))
    region = str(criteria.get("region") or criteria.get("postcode") or "").strip().upper()
    allowed = set(criteria.get("signals") or ["below_market", "high_turnover", "long_hold", "overseas_owner"])
    rows = connection.execute("SELECT uprn,address_full,postcode FROM property_base WHERE (?='' OR postcode LIKE ?)", (region, f"{region}%")).fetchall()
    matches = []
    for uprn, address, postcode in rows:
        signals = [dict(zip(("signal_type", "value", "strength", "computed_at"), row)) for row in connection.execute("SELECT signal_type,value,strength,computed_at FROM property_signals WHERE uprn=?", (uprn,)).fetchall() if row[0] in allowed]
        score = score_signals(signals)
        if score["score"] < min_score:
            continue
        match_id = uuid.uuid5(uuid.NAMESPACE_URL, f"keprix:saved-search:{search_id}:{uprn}").hex
        connection.execute("INSERT INTO property_saved_search_matches (id,saved_search_id,uprn,score,signals_json,status,found_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(saved_search_id,uprn) DO UPDATE SET score=excluded.score,signals_json=excluded.signals_json,found_at=excluded.found_at", (match_id, search_id, uprn, score["score"], json.dumps({"address": address, "postcode": postcode, **score}), "new", _now()))
        matches.append({"id": match_id, "uprn": uprn, "score": score["score"], "signals": score, "status": "new"})
    connection.execute("UPDATE property_saved_searches SET last_run_at=? WHERE id=? AND workspace_id=?", (_now(), search_id, workspace_id))
    connection.commit()
    return {"status": "ok", "search_id": search_id, "matches": sorted(matches, key=lambda item: (-item["score"], item["uprn"]))}


def run_all_active_saved_searches(*, connection=None) -> list[dict[str, Any]]:
    connection = _connection(connection)
    ensure_schema(connection)
    rows = connection.execute("SELECT id,workspace_id FROM property_saved_searches WHERE active=1").fetchall()
    return [run_saved_search(row[0], row[1], connection=connection) for row in rows]


def update_match_status(match_id: str, workspace_id: str, status: str, *, connection=None) -> bool:
    if status not in {"new", "viewed", "dismissed", "handed_off"}:
        return False
    connection = _connection(connection)
    changed = connection.execute("UPDATE property_saved_search_matches SET status=? WHERE id=? AND saved_search_id IN (SELECT id FROM property_saved_searches WHERE workspace_id=?)", (status, match_id, workspace_id)).rowcount
    connection.commit()
    return bool(changed)


def propose_handoff(match_id: str, workspace_id: str, *, connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    existing = connection.execute("SELECT deal_id FROM property_deal_handoffs WHERE match_id=? AND workspace_id=?", (match_id, workspace_id)).fetchone()
    if existing:
        return {"status": "already_handed_off", "deal_id": existing[0], "match_id": match_id}
    row = connection.execute("SELECT m.uprn,m.score,m.status FROM property_saved_search_matches m JOIN property_saved_searches s ON s.id=m.saved_search_id WHERE m.id=? AND s.workspace_id=?", (match_id, workspace_id)).fetchone()
    if not row:
        return {"status": "not_found", "match_id": match_id}
    if row[2] == "dismissed":
        return {"status": "dismissed", "match_id": match_id}
    from keprix.crm.store import get_crm_store
    lead = get_crm_store().upsert_lead(workspace_id, name=f"Property {row[0]}", company_name=f"Property {row[0]}", source="property_saved_search", external_source_id=f"property:{row[0]}", custom_fields={"property_uprn": row[0], "saved_search_score": row[1]})
    deal = get_crm_store().create_deal(workspace_id, f"Property {row[0]}", lead_id=lead["id"], source="property_saved_search", external_source_id=f"property_saved_search:{match_id}", scores={"property_score": row[1]})
    connection.execute("INSERT INTO property_deal_handoffs (id,workspace_id,match_id,deal_id,created_at) VALUES (?,?,?,?,?)", (uuid.uuid4().hex, workspace_id, match_id, deal["id"], _now()))
    connection.execute("UPDATE property_saved_search_matches SET status='handed_off' WHERE id=?", (match_id,))
    connection.commit()
    return {"status": "handed_off", "match_id": match_id, "lead_id": lead["id"], "deal_id": deal["id"]}
