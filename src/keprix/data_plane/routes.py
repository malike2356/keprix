"""Data plane HTTP routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.data_architecture.control_plane import get_control_plane
from keprix.data_architecture.data_plane import get_workspace_data_plane
from keprix.data_architecture.exports import export_dataset_copy
from keprix.data_architecture.integrity import planes_integrity
from keprix.data_plane.catalog import get_dataset_catalog
from keprix.data_plane.duckdb_engine import import_csv_dataset, import_parquet_dataset, run_query
from keprix.data_plane.tabular_import import import_excel_dataset, import_spss_dataset, supported_tabular_suffixes

router = APIRouter(prefix="/api/data", tags=["data-plane"])


@router.get("/planes/status")
async def planes_status() -> dict[str, Any]:
    return await planes_integrity()


@router.get("/catalog")
async def data_catalog() -> dict[str, Any]:
    return {
        "control_plane": get_control_plane().status(),
        "datasets": get_dataset_catalog().list(),
    }


class QueryBody(BaseModel):
    dataset_id: str
    sql: str = Field(..., min_length=1)


@router.get("/datasets")
async def list_datasets() -> dict[str, Any]:
    return {"datasets": get_dataset_catalog().list()}


@router.post("/datasets")
async def create_dataset_metadata(name: str, format: str = "csv") -> dict[str, Any]:
    dataset_id = f"ds-pending-{name[:12]}"
    get_workspace_data_plane().register_dataset_version(
        dataset_id=dataset_id,
        name=name,
        fmt=format,
        path="",
        db_path=None,
        engine=None,
        row_count=None,
        lineage={"created": "metadata_only"},
    )
    return {"dataset_id": dataset_id, "name": name, "format": format}


@router.get("/datasets/{dataset_id}/versions")
async def dataset_versions(dataset_id: str) -> dict[str, Any]:
    versions = get_workspace_data_plane().list_dataset_versions(dataset_id)
    if not versions:
        raise HTTPException(404, "Dataset not found")
    return {"items": versions}


@router.post("/import")
async def import_data(name: str, file: UploadFile = File(...)) -> dict[str, Any]:
    return await import_dataset(name=name, file=file)


@router.post("/export")
async def export_data(dataset_id: str, format: str = "csv") -> dict[str, Any]:
    row = get_dataset_catalog().get(dataset_id)
    if row is None:
        raise HTTPException(404, "Dataset not found")
    source = Path(str(row["path"]))
    with tempfile.TemporaryDirectory() as tmp:
        result = export_dataset_copy(source, Path(tmp), fmt=format)
    return {"dataset_id": dataset_id, **result}


@router.get("/import/formats")
async def import_formats() -> dict[str, Any]:
    return {"formats": sorted(suffix.lstrip(".") for suffix in supported_tabular_suffixes())}


@router.post("/datasets/import")
async def import_dataset(
    name: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    allowed = supported_tabular_suffixes()
    if suffix.lower() not in allowed:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            400,
            f"Unsupported import format `{suffix}`. Supported: {', '.join(sorted(allowed))}",
        )

    try:
        if suffix.lower() == ".parquet":
            meta = import_parquet_dataset(tmp_path, table_name="dataset")
        elif suffix.lower() in {".xlsx", ".xlsm"}:
            meta = import_excel_dataset(tmp_path, table_name="dataset")
        elif suffix.lower() == ".sav":
            meta = import_spss_dataset(tmp_path, table_name="dataset")
        else:
            meta = import_csv_dataset(tmp_path, table_name="dataset")
    except ImportError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(400, str(exc)) from exc

    row = get_dataset_catalog().register(
        name=name,
        source_path=tmp_path,
        format=suffix.lstrip("."),
        row_count=meta.get("row_count"),
        db_path=meta.get("db_path"),
        engine=meta.get("engine"),
    )
    get_control_plane().link_data_plane("default", str(get_workspace_data_plane().root))
    lineage: dict[str, Any] = {"import": "data_plane", "source_format": meta.get("source_format", suffix.lstrip("."))}
    if meta.get("metadata_path"):
        lineage["metadata_path"] = meta["metadata_path"]
    if meta.get("variable_labels"):
        lineage["variable_labels"] = meta["variable_labels"]
    if meta.get("value_labels"):
        lineage["value_labels"] = meta["value_labels"]
    if meta.get("sheet"):
        lineage["sheet"] = meta["sheet"]
    get_workspace_data_plane().register_dataset_version(
        dataset_id=row["id"],
        name=name,
        fmt=suffix.lstrip("."),
        path=row["path"],
        db_path=row.get("db_path"),
        engine=row.get("engine"),
        row_count=row.get("row_count"),
        lineage=lineage,
    )
    return {"dataset": row}


@router.post("/query")
async def query_dataset(body: QueryBody) -> dict[str, Any]:
    row = get_dataset_catalog().get(body.dataset_id)
    if row is None:
        raise HTTPException(404, "Dataset not found")
    db_path = Path(str(row.get("db_path") or ""))
    if not db_path.exists():
        db_path = Path(str(row["path"])).with_suffix(".duckdb")
    if not db_path.exists():
        db_path = Path(str(row["path"])).with_suffix(".sqlite")
    if not db_path.exists():
        raise HTTPException(400, "Dataset not indexed")
    sql = body.sql.strip()
    if not sql.lower().startswith("select"):
        raise HTTPException(400, "Only SELECT queries are allowed")
    engine = "duckdb" if db_path.suffix == ".duckdb" else "sqlite"
    return run_query(db_path, sql, engine=engine)


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str) -> dict[str, bool]:
    if not get_dataset_catalog().remove(dataset_id):
        raise HTTPException(404, "Dataset not found")
    return {"deleted": True}
