"""Property signal discovery and CRM materialization."""

from __future__ import annotations

from typing import Any

from .refresh import _connection
from .schema import ensure_schema
from .scoring import score_signals
from .scoring import WEIGHTS


def get_config(workspace_id: str = "default", connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT enabled_signals,min_score,max_results,region_filter,updated_at FROM property_discovery_configs WHERE workspace_id=?", (workspace_id,)).fetchone()
    if not row:
        return {"workspace_id": workspace_id, "enabled_signals": ["below_market", "high_turnover", "long_hold", "overseas_owner"], "min_score": 0.5, "max_results": 50, "region_filter": "", "updated_at": ""}
    return {"workspace_id": workspace_id, "enabled_signals": [x for x in row[0].split(",") if x], "min_score": float(row[1]), "max_results": int(row[2]), "region_filter": row[3], "updated_at": row[4]}


def set_config(workspace_id: str, values: dict[str, Any], connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    current = get_config(workspace_id, connection)
    allowed = set(values.get("enabled_signals", current["enabled_signals"])) & set(WEIGHTS)
    signals = ",".join(sorted(allowed))
    minimum = max(0.0, min(1.0, float(values.get("min_score", current["min_score"]))))
    limit = max(1, min(1000, int(values.get("max_results", current["max_results"]))))
    region = str(values.get("region_filter", current["region_filter"]) or "").strip().upper()
    from .refresh import now
    connection.execute("INSERT INTO property_discovery_configs (workspace_id,enabled_signals,min_score,max_results,region_filter,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(workspace_id) DO UPDATE SET enabled_signals=excluded.enabled_signals,min_score=excluded.min_score,max_results=excluded.max_results,region_filter=excluded.region_filter,updated_at=excluded.updated_at", (workspace_id, signals, minimum, limit, region, now()))
    connection.commit()
    return get_config(workspace_id, connection)


def discover(workspace_id: str = "default", *, connection=None, materialize: bool = False) -> dict[str, Any]:
    connection = _connection(connection)
    config = get_config(workspace_id, connection)
    allowed = set(config["enabled_signals"])
    rows = connection.execute("SELECT uprn,address_full,postcode FROM property_base WHERE (?='' OR postcode LIKE ?) ORDER BY uprn", (config["region_filter"], f"{config['region_filter']}%")).fetchall()
    candidates = []
    for uprn, address, postcode in rows:
        raw = connection.execute("SELECT signal_type,value,strength,computed_at FROM property_signals WHERE uprn=?", (uprn,)).fetchall()
        signals = [dict(zip(("signal_type", "value", "strength", "computed_at"), row)) for row in raw if row[0] in allowed]
        scored = score_signals(signals)
        if scored["score"] < config["min_score"]:
            continue
        candidates.append({"uprn": uprn, "address": address, "postcode": postcode, **scored, "source": "property_signal"})
    candidates.sort(key=lambda item: (-item["score"], item["uprn"]))
    candidates = candidates[: config["max_results"]]
    if materialize and candidates:
        from keprix.crm.store import get_crm_store
        for item in candidates:
            get_crm_store().upsert_lead(workspace_id, name=item["address"], company_name=item["address"], locality=item["postcode"], source="property_signal", external_source_id=f"property:{item['uprn']}", custom_fields={"property_uprn": item["uprn"], "motivated_seller_score": item["score"], "signals": item["signals"]})
    return {"workspace_id": workspace_id, "candidates": candidates, "materialized": bool(materialize)}
