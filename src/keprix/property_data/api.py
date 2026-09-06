"""Derived, attribution-preserving reads over owned property data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .refresh import _connection
from .schema import ensure_schema


def _record(connection, *, workspace_id: str, key_id: str, endpoint: str, uprn: str = "", postcode: str = "", idempotency_key: str = "") -> None:
    try:
        from keprix.billing.property_metering import meter_property_api_call

        meter_property_api_call(workspace_id=workspace_id, endpoint=endpoint, connection=connection, key_id=key_id, uprn=uprn, postcode=postcode, idempotency_key=idempotency_key)
    except Exception:
        pass


def lookup(*, uprn: str = "", postcode: str = "", workspace_id: str = "default", key_id: str = "", connection=None, idempotency_key: str = "") -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT uprn,address_full,postcode FROM property_base WHERE (? <> '' AND uprn=?) OR (? <> '' AND postcode=?) LIMIT 1", (uprn, uprn, postcode.upper(), postcode.upper())).fetchone()
    if not row:
        result = {"found": False, "source": "HM Land Registry Price Paid Data and EPC open data"}
        _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="lookup", uprn=uprn, postcode=postcode, idempotency_key=idempotency_key)
        return result
    signals = [dict(zip(("signal_type", "value", "strength", "computed_at"), item)) for item in connection.execute("SELECT signal_type,value,strength,computed_at FROM property_signals WHERE uprn=? ORDER BY signal_type", (row[0],)).fetchall()]
    _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="lookup", uprn=row[0], postcode=row[2], idempotency_key=idempotency_key)
    return {"found": True, "uprn": row[0], "address": row[1], "postcode": row[2], "signals": signals, "source": "Keprix derived signals from HM Land Registry and EPC open data"}


def sold_prices(*, postcode: str = "", workspace_id: str = "default", key_id: str = "", connection=None, idempotency_key: str = "") -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT COUNT(*),AVG(s.price_gbp),MIN(s.price_gbp),MAX(s.price_gbp) FROM property_sold_prices s JOIN property_base b ON b.uprn=s.uprn WHERE b.postcode=?", (postcode.upper(),)).fetchone()
    _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="sold-prices", postcode=postcode, idempotency_key=idempotency_key)
    return {"postcode": postcode.upper(), "count": int(row[0] or 0), "mean_price_gbp": row[1], "min_price_gbp": row[2], "max_price_gbp": row[3], "source": "HM Land Registry Price Paid Data, aggregated"}


def epc(*, uprn: str, workspace_id: str = "default", key_id: str = "", connection=None, idempotency_key: str = "") -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    row = connection.execute("SELECT current_energy_rating,potential_energy_rating,current_energy_efficiency,inspection_date,floor_area_m2 FROM property_epc WHERE uprn=? ORDER BY inspection_date DESC LIMIT 1", (uprn,)).fetchone()
    _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="epc", uprn=uprn, idempotency_key=idempotency_key)
    return {"uprn": uprn, "found": bool(row), "epc": dict(zip(("current_rating", "potential_rating", "efficiency", "inspection_date", "floor_area_m2"), row)) if row else None, "source": "EPC open data"}


def ownership(*, uprn: str, workspace_id: str = "default", key_id: str = "", connection=None, idempotency_key: str = "") -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    count = int(connection.execute("SELECT COUNT(*) FROM property_company_ownership WHERE uprn=?", (uprn,)).fetchone()[0])
    _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="ownership", uprn=uprn, idempotency_key=idempotency_key)
    return {"uprn": uprn, "overseas_owner": count > 0, "company_count": count, "source": "CCOD/OCOD derived ownership signal"}


def signals(*, uprn: str, workspace_id: str = "default", key_id: str = "", connection=None, idempotency_key: str = "") -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    rows = connection.execute("SELECT signal_type,value,strength,computed_at FROM property_signals WHERE uprn=? ORDER BY signal_type", (uprn,)).fetchall()
    _record(connection, workspace_id=workspace_id, key_id=key_id, endpoint="signals", uprn=uprn, idempotency_key=idempotency_key)
    return {"uprn": uprn, "signals": [dict(zip(("signal_type", "value", "strength", "computed_at"), row)) for row in rows], "source": "Keprix deterministic property signals"}
