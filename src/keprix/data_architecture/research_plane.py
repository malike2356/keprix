"""Analytical plane helpers (DuckDB, Parquet, exports)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.data_plane.duckdb_engine import import_csv_dataset, import_parquet_dataset, run_query
from keprix.data_plane.tabular_import import import_excel_dataset, import_spss_dataset


def import_dataset_file(path: Path, *, table_name: str = "dataset") -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return import_parquet_dataset(path, table_name=table_name)
    if suffix in {".csv", ".tsv"}:
        return import_csv_dataset(path, table_name=table_name)
    if suffix in {".xlsx", ".xlsm"}:
        return import_excel_dataset(path, table_name=table_name)
    if suffix == ".sav":
        return import_spss_dataset(path, table_name=table_name)
    raise ValueError(f"Unsupported analytical import format: {suffix}")


def query_dataset(db_path: Path, sql: str, *, engine: str = "duckdb") -> dict[str, Any]:
    return run_query(db_path, sql, engine=engine)
