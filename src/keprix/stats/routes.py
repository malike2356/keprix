"""Statistical analysis routes."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.analytics.statistical_methods import describe
from keprix.auth.dependencies import get_current_user
from keprix.data_architecture.exports import export_metadata_bundle
from keprix.data_architecture.research_plane import import_dataset_file
from keprix.data_plane.catalog import get_dataset_catalog
from keprix.data_architecture.data_plane import get_workspace_data_plane

router = APIRouter(prefix="/api/stats", tags=["stats"])


class AnalyzeBody(BaseModel):
    dataset_id: str
    column: str = Field(..., min_length=1)


@router.post("/import")
async def stats_import(name: str, file: UploadFile = File(...), _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        meta = import_dataset_file(tmp_path)
    except ValueError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImportError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = get_dataset_catalog().register(
        name=name,
        source_path=tmp_path,
        format=suffix.lstrip("."),
        row_count=meta.get("row_count"),
        db_path=meta.get("db_path"),
        engine=meta.get("engine"),
    )
    version = get_workspace_data_plane().register_dataset_version(
        dataset_id=row["id"],
        name=name,
        fmt=suffix.lstrip("."),
        path=row["path"],
        db_path=row.get("db_path"),
        engine=row.get("engine"),
        row_count=row.get("row_count"),
        lineage={
            "import": "stats_import",
            "source_format": meta.get("source_format", suffix.lstrip(".")),
            "metadata_path": meta.get("metadata_path"),
            "variable_labels": meta.get("variable_labels"),
            "value_labels": meta.get("value_labels"),
            "sheet": meta.get("sheet"),
        },
    )
    return {"dataset": row, "version": version}


@router.post("/analyze")
async def stats_analyze(body: AnalyzeBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    row = get_dataset_catalog().get(body.dataset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    path = Path(str(row["path"]))
    values: list[float] = []
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for record in reader:
                raw = record.get(body.column)
                if raw is None or raw == "":
                    continue
                try:
                    values.append(float(raw))
                except ValueError:
                    continue
    summary = describe(values)
    return {
        "dataset_id": body.dataset_id,
        "column": body.column,
        "summary": summary,
        "dataset_version": get_workspace_data_plane().list_dataset_versions(body.dataset_id),
    }


@router.post("/export")
async def stats_export(body: AnalyzeBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    analysis = await stats_analyze(body, _user)
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / f"{body.dataset_id}-codebook.json"
        export_metadata_bundle(analysis, dest)
        payload = json.loads(dest.read_text(encoding="utf-8"))
    return {"codebook": payload}
