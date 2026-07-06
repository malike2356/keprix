"""DuckDB query engine with CSV fallback."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any


def _duckdb_available() -> bool:
    try:
        import duckdb  # noqa: F401

        return True
    except ImportError:
        return False


def import_parquet_dataset(path: Path, *, table_name: str = "dataset") -> dict[str, Any]:
    import duckdb

    db_path = path.with_suffix(".duckdb")
    conn = duckdb.connect(str(db_path))
    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet(?)", [str(path)])
    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    conn.close()
    return {"engine": "duckdb", "db_path": str(db_path), "table": table_name, "row_count": int(count)}


def import_csv_dataset(path: Path, *, table_name: str = "dataset") -> dict[str, Any]:
    """Import a CSV file into DuckDB or SQLite fallback."""
    if _duckdb_available():
        import duckdb

        db_path = path.with_suffix(".duckdb")
        conn = duckdb.connect(str(db_path))
        conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)", [str(path)])
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        conn.close()
        return {"engine": "duckdb", "db_path": str(db_path), "table": table_name, "row_count": int(count)}

    db_path = path.with_suffix(".sqlite")
    conn = sqlite3.connect(db_path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            conn.close()
            return {"engine": "sqlite", "db_path": str(db_path), "table": table_name, "row_count": 0}
        columns = reader.fieldnames
        placeholders = ", ".join("?" for _ in columns)
        col_sql = ", ".join(f'"{c}"' for c in columns)
        conn.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({col_sql})')
        rows = [tuple(row.get(c, "") for c in columns) for row in reader]
        conn.executemany(f"INSERT INTO {table_name} VALUES ({placeholders})", rows)
        conn.commit()
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        conn.close()
        return {"engine": "sqlite", "db_path": str(db_path), "table": table_name, "row_count": int(count)}


def run_query(db_path: Path, sql: str, *, engine: str = "duckdb") -> dict[str, Any]:
    """Run a read-only SQL query against a dataset database."""
    if engine == "duckdb" and _duckdb_available():
        import duckdb

        conn = duckdb.connect(str(db_path), read_only=True)
        result = conn.execute(sql).fetchdf()
        conn.close()
        return {"columns": list(result.columns), "rows": result.to_dict(orient="records")}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(sql)
    rows = [dict(row) for row in cursor.fetchall()]
    columns = [d[0] for d in cursor.description] if cursor.description else []
    conn.close()
    return {"columns": columns, "rows": rows}
