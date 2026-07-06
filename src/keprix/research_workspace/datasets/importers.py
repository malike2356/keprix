"""Dataset importers for research workflows."""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from keprix.data_architecture.research_plane import import_dataset_file
from keprix.data_plane.duckdb_engine import import_csv_dataset


def _copy_original(source: Path, originals_dir: Path) -> Path:
    originals_dir.mkdir(parents=True, exist_ok=True)
    dest = originals_dir / f"original{source.suffix.lower() or '.dat'}"
    shutil.copy2(source, dest)
    return dest


def import_json_dataset(path: Path, *, table_name: str = "dataset") -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("records") or payload.get("data") or [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("JSON dataset must be an object or array")
    if not rows:
        raise ValueError("JSON dataset is empty")
    csv_path = path.with_suffix(".converted.csv")
    columns = sorted({key for row in rows if isinstance(row, dict) for key in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            if isinstance(row, dict):
                writer.writerow({column: row.get(column, "") for column in columns})
    result = import_csv_dataset(csv_path, table_name=table_name)
    return {**result, "source_format": "json"}


def import_sqlite_table(path: Path, *, table_name: str) -> dict[str, Any]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
    conn.close()
    if not rows:
        raise ValueError(f"SQLite table {table_name} is empty")
    csv_path = path.with_suffix(f".{table_name}.csv")
    columns = rows[0].keys()
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    result = import_csv_dataset(csv_path, table_name="dataset")
    return {**result, "source_format": "sqlite", "sqlite_table": table_name}


def import_postgres_query(
    *,
    dsn: str,
    sql: str,
    export_path: Path,
) -> dict[str, Any]:
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise ImportError("Postgres export requires psycopg; pip install psycopg[binary]") from exc
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [desc.name for desc in cursor.description or []]
            rows = cursor.fetchall()
    if not columns:
        raise ValueError("Postgres query returned no columns")
    with export_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: value for column, value in zip(columns, row)})
    result = import_csv_dataset(export_path, table_name="dataset")
    return {**result, "source_format": "postgres", "query": sql}


def import_research_dataset(
    source_path: Path,
    *,
    originals_dir: Path,
    table_name: str = "dataset",
    sqlite_table: str | None = None,
) -> dict[str, Any]:
    original_copy = _copy_original(source_path, originals_dir)
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        meta = import_json_dataset(source_path, table_name=table_name)
    elif suffix in {".sqlite", ".db"} and sqlite_table:
        meta = import_sqlite_table(source_path, table_name=sqlite_table)
    elif suffix == ".sps":
        meta = {
            "source_format": "pspp_syntax",
            "row_count": 0,
            "engine": None,
            "db_path": None,
            "note": "PSPP syntax stored; execute in PSPP and import resulting data separately.",
        }
    else:
        meta = import_dataset_file(source_path, table_name=table_name)
    meta["original_path"] = str(original_copy)
    meta["imported_from"] = str(source_path)
    return meta


def read_preview_rows(data_path: Path, *, limit: int = 5) -> tuple[list[str], list[dict[str, Any]]]:
    suffix = data_path.suffix.lower()
    if suffix == ".csv":
        with data_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            rows = [dict(row) for _, row in zip(range(limit), reader)]
        return columns, rows
    if suffix == ".json" and data_path.name.endswith(".schema.json"):
        schema = json.loads(data_path.read_text(encoding="utf-8"))
        columns = [item["name"] for item in schema.get("variables", [])]
        return columns, []
    return [], []
