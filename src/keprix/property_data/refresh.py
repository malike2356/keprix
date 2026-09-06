"""Refresh orchestration and deterministic property signals."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import date
import statistics
from typing import Any

from .ingest import ingest_epc, ingest_ownership, ingest_ppd, ingest_uprn, now, rows_from_csv
from .schema import ensure_schema


def _connection(connection=None):
    if connection is not None:
        return connection
    from keprix.crm.store import get_crm_store

    return get_crm_store()._conn


def compute_signals(connection) -> int:
    timestamp = now()
    rows = connection.execute("SELECT uprn, COUNT(*) FROM property_sold_prices WHERE uprn <> '' GROUP BY uprn").fetchall()
    written = 0
    postcode_rows = connection.execute("SELECT postcode, price_gbp FROM property_sold_prices s JOIN property_base b ON b.uprn=s.uprn WHERE b.postcode <> '' ORDER BY postcode, price_gbp").fetchall()
    grouped: dict[str, list[float]] = {}
    for postcode, price in postcode_rows:
        grouped.setdefault(str(postcode), []).append(float(price))
    postcode_median = {postcode: statistics.median(prices) for postcode, prices in grouped.items()}
    for uprn, count in rows:
        sales = connection.execute("SELECT price_gbp, sale_date FROM property_sold_prices WHERE uprn=? ORDER BY sale_date", (uprn,)).fetchall()
        if int(count or 0) >= 2:
            connection.execute("INSERT INTO property_signals (id,uprn,signal_type,value,strength,computed_at) VALUES (?,?,?,?,?,?) ON CONFLICT(uprn,signal_type) DO UPDATE SET value=excluded.value,strength=excluded.strength,computed_at=excluded.computed_at", (f"{uprn}:high_turnover", uprn, "high_turnover", str(count), min(1.0, int(count) / 4), timestamp))
            written += 1
        base = connection.execute("SELECT postcode FROM property_base WHERE uprn=?", (uprn,)).fetchone()
        average = postcode_median.get(str(base[0]), 0) if base else 0
        latest = int(sales[-1][0]) if sales else 0
        if average and latest < average * 0.8:
            connection.execute("INSERT INTO property_signals (id,uprn,signal_type,value,strength,computed_at) VALUES (?,?,?,?,?,?) ON CONFLICT(uprn,signal_type) DO UPDATE SET value=excluded.value,strength=excluded.strength,computed_at=excluded.computed_at", (f"{uprn}:below_market", uprn, "below_market", str(latest), min(1.0, (average - latest) / average), timestamp))
            written += 1
        if sales and len(sales) == 1 and sales[0][1]:
            try:
                held_years = (date.today() - date.fromisoformat(str(sales[0][1]))).days / 365.25
            except ValueError:
                held_years = 0
            if held_years > 15:
                connection.execute("INSERT INTO property_signals (id,uprn,signal_type,value,strength,computed_at) VALUES (?,?,?,?,?,?) ON CONFLICT(uprn,signal_type) DO UPDATE SET value=excluded.value,strength=excluded.strength,computed_at=excluded.computed_at", (f"{uprn}:long_hold", uprn, "long_hold", sales[0][1], min(1.0, held_years / 30), timestamp))
                written += 1
    ownership = connection.execute("SELECT DISTINCT uprn FROM property_company_ownership WHERE uprn <> ''").fetchall()
    for (uprn,) in ownership:
        connection.execute("INSERT INTO property_signals (id,uprn,signal_type,value,strength,computed_at) VALUES (?,?,?,?,?,?) ON CONFLICT(uprn,signal_type) DO UPDATE SET value=excluded.value,strength=excluded.strength,computed_at=excluded.computed_at", (f"{uprn}:overseas_owner", uprn, "overseas_owner", "true", 1.0, timestamp))
        written += 1
    connection.commit()
    return written


def refresh_all(connection=None, *, ppd_rows=None, epc_rows=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    report: dict[str, Any] = {"status": "ok", "sources": {}}
    for source, rows, ingest in (("ppd", ppd_rows, ingest_ppd), ("epc", epc_rows, ingest_epc), ("uprn", None, ingest_uprn), ("ownership", None, ingest_ownership)):
        path = os.environ.get(f"KEPRIX_PROPERTY_{source.upper()}_CSV", "").strip()
        try:
            count = ingest(connection, rows if rows is not None else rows_from_csv(Path(path))) if rows is not None or path else 0
            status = "live" if count else "disabled"
            connection.execute("INSERT INTO property_ingest_state (source,last_ingest_at,last_status,row_count,error) VALUES (?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET last_ingest_at=excluded.last_ingest_at,last_status=excluded.last_status,row_count=excluded.row_count,error=''", (source, now(), status, count, ""))
            report["sources"][source] = {"status": status, "row_count": count}
        except Exception as exc:
            connection.execute("INSERT INTO property_ingest_state (source,last_ingest_at,last_status,row_count,error) VALUES (?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET last_ingest_at=excluded.last_ingest_at,last_status=excluded.last_status,row_count=0,error=excluded.error", (source, now(), "error", 0, str(exc)))
            connection.commit()
            report["sources"][source] = {"status": "error", "error": str(exc)}
    report["signals"] = compute_signals(connection)
    return report


def dataset_status(connection=None) -> dict[str, Any]:
    connection = _connection(connection)
    ensure_schema(connection)
    tables = ("property_base", "property_sold_prices", "property_epc", "property_company_ownership", "property_signals")
    counts = {table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}
    source_rows = connection.execute("SELECT source,last_ingest_at,last_status,row_count,error FROM property_ingest_state ORDER BY source").fetchall()
    source_columns = ("source", "last_ingest_at", "last_status", "row_count", "error")
    sources = [
        dict(zip(source_columns, row)) if not hasattr(row, "keys") else dict(row)
        for row in source_rows
    ]
    return {"dataset_status": sources, "counts": counts, "total_rows": sum(counts.values())}
