"""Streaming-friendly, idempotent property dataset ingestion."""

from __future__ import annotations

import csv
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .schema import ensure_schema


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rows_from_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        yield from csv.DictReader(handle)


def _value(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if row.get(key) is not None and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def _base(connection, row: dict[str, Any], timestamp: str) -> None:
    address = _value(row, "address_full", "address", "PAON", "paon")
    postcode = _value(row, "postcode", "Postcode").upper()
    uprn = _value(row, "uprn", "UPRN") or "addr-" + hashlib.sha256(f"{address}|{postcode}".encode()).hexdigest()[:24]
    connection.execute("INSERT INTO property_base (uprn,address_full,postcode,address_hash,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?) ON CONFLICT(uprn) DO UPDATE SET last_seen_at=excluded.last_seen_at", (uprn, address or postcode or uprn, postcode, hashlib.sha256(f"{address}|{postcode}".encode()).hexdigest(), timestamp, timestamp))


def ingest_ppd(connection, rows: Iterable[dict[str, Any]]) -> int:
    ensure_schema(connection)
    count = 0
    timestamp = now()
    for row in rows:
        transaction = _value(row, "transaction_id", "Transaction unique identifier", "id") or str(uuid.uuid4())
        price = int(float(_value(row, "price_gbp", "Price", "price") or 0))
        if price <= 0:
            continue
        _base(connection, row, timestamp)
        uprn = _value(row, "uprn", "UPRN") or ""
        cursor = connection.execute("INSERT INTO property_sold_prices (id,uprn,price_gbp,sale_date,property_type,tenure,new_build,ingested_at,transaction_id) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(transaction_id) DO NOTHING", (transaction, uprn, price, _value(row, "sale_date", "Date of Transfer", "date"), _value(row, "property_type", "Property Type"), _value(row, "tenure", "Duration"), int(_value(row, "new_build", "New build") == "Y"), timestamp, transaction))
        count += int(cursor.rowcount > 0)
    connection.commit()
    return count


def ingest_epc(connection, rows: Iterable[dict[str, Any]]) -> int:
    ensure_schema(connection)
    count = 0
    timestamp = now()
    for row in rows:
        certificate = _value(row, "certificate_id", "LMK_KEY", "id") or str(uuid.uuid4())
        _base(connection, row, timestamp)
        cursor = connection.execute("INSERT INTO property_epc (id,uprn,current_energy_rating,potential_energy_rating,current_energy_efficiency,inspection_date,floor_area_m2,ingested_at,certificate_id) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(certificate_id) DO NOTHING", (certificate, _value(row, "uprn", "UPRN"), _value(row, "current_energy_rating", "CURRENT_ENERGY_RATING"), _value(row, "potential_energy_rating", "POTENTIAL_ENERGY_RATING"), int(float(_value(row, "current_energy_efficiency", "CURRENT_ENERGY_EFFICIENCY") or 0)) or None, _value(row, "inspection_date", "INSPECTION_DATE"), float(_value(row, "floor_area_m2", "TOTAL_FLOOR_AREA") or 0) or None, timestamp, certificate))
        count += int(cursor.rowcount > 0)
    connection.commit()
    return count


def ingest_uprn(connection, rows: Iterable[dict[str, Any]]) -> int:
    """Load address-to-UPRN rows without retaining the source file in memory."""
    ensure_schema(connection)
    count = 0
    timestamp = now()
    for row in rows:
        uprn = _value(row, "uprn", "UPRN")
        if not uprn:
            continue
        address = _value(row, "address_full", "address", "ADDRESS", "addressable_object")
        postcode = _value(row, "postcode", "Postcode", "POSTCODE").upper()
        address_hash = hashlib.sha256(f"{address}|{postcode}".encode()).hexdigest()
        exists = connection.execute("SELECT 1 FROM property_base WHERE uprn=?", (uprn,)).fetchone()
        cursor = connection.execute(
            "INSERT INTO property_base (uprn,address_full,postcode,address_hash,first_seen_at,last_seen_at) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(uprn) DO UPDATE SET address_full=excluded.address_full,postcode=excluded.postcode,address_hash=excluded.address_hash,last_seen_at=excluded.last_seen_at",
            (uprn, address or postcode or uprn, postcode, address_hash, timestamp, timestamp),
        )
        count += int(exists is None and cursor.rowcount > 0)
    connection.commit()
    return count


def ingest_ownership(connection, rows: Iterable[dict[str, Any]]) -> int:
    """Load CCOD/OCOD-style ownership rows, deduplicated by source identity."""
    ensure_schema(connection)
    count = 0
    timestamp = now()
    for row in rows:
        uprn = _value(row, "uprn", "UPRN")
        company = _value(row, "company_number", "Company Number", "company_no")
        if not uprn or not company:
            continue
        identity = hashlib.sha256(f"{uprn}|{company}".encode()).hexdigest()
        cursor = connection.execute(
            "INSERT INTO property_company_ownership (id,uprn,company_number,country_of_incorporation,source,ingested_at) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(id) DO NOTHING",
            (identity, uprn, company, _value(row, "country_of_incorporation", "Country"), _value(row, "source") or "ccod_ocod", timestamp),
        )
        count += int(cursor.rowcount > 0)
    connection.commit()
    return count
