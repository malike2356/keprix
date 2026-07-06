"""Dataset manager HTTP routes."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from keprix.analytics.jamovi.export_bridge import prepare_export_package
from keprix.auth.dependencies import get_current_user
from keprix.research_workspace.datasets.codebook import Codebook
from keprix.research_workspace.datasets.dataset import DatasetManager
from keprix.research_workspace.store import get_research_workspace_store

router = APIRouter(prefix="/api/research/datasets", tags=["research-datasets"])


class CodebookBody(BaseModel):
    codebook: dict[str, Any]


class TransformBody(BaseModel):
    transform: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class ExportBody(BaseModel):
    format: Literal["csv", "parquet", "json-schema", "pspp", "r", "python", "jamovi"] = "csv"


def _manager() -> DatasetManager:
    return DatasetManager(get_research_workspace_store())


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("user_id") or user.get("username") or "default")


@router.post("/projects/{project_id}/import")
async def import_dataset(
    project_id: str,
    name: str,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    store = get_research_workspace_store()
    if store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    suffix = Path(file.filename or "data.csv").suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        result = _manager().import_file(
            project_id,
            source_path=tmp_path,
            name=name,
            owner=_user_id(user),
        )
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return result


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    dataset = _manager().get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return _manager().preview(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{dataset_id}/codebook")
async def update_codebook(
    dataset_id: str,
    body: CodebookBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    manager = _manager()
    if manager.get_dataset(dataset_id) is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    codebook = Codebook.from_dict(body.codebook)
    codebook.dataset_id = dataset_id
    saved = manager.save_codebook(codebook)
    return {"codebook": saved.to_dict()}


@router.post("/{dataset_id}/transform")
async def transform_dataset(
    dataset_id: str,
    body: TransformBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return _manager().transform(dataset_id, transform=body.transform, params=body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/export")
async def export_dataset_route(
    dataset_id: str,
    body: ExportBody,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        return _manager().export(dataset_id, fmt=body.format)
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{dataset_id}/export/download")
async def download_dataset_export(
    dataset_id: str,
    format: Literal["csv", "pspp", "jamovi"] = Query("jamovi"),
    _user: dict = Depends(get_current_user),
) -> Response:
    manager = _manager()
    try:
        if format == "jamovi":
            preview = manager.preview(dataset_id)
            rows = preview.get("rows") or []
            if not rows:
                raise ValueError("Dataset has no rows to export")
            columns = [{"name": column} for column in preview.get("columns") or list(rows[0].keys())]
            package = prepare_export_package(rows, columns=columns, dataset_name=dataset_id)
            return Response(
                content=package["package_bytes"],
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{package["package_filename"]}"',
                },
            )
        result = manager.export(dataset_id, fmt=format)
        path = Path(str(result.get("path") or ""))
        if not path.exists():
            raise ValueError("Export file was not created")
        media_types = {
            ".csv": "text/csv",
            ".sps": "text/plain",
        }
        return FileResponse(
            path,
            media_type=media_types.get(path.suffix.lower(), "application/octet-stream"),
            filename=path.name,
        )
    except (ValueError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/validate")
async def validate_dataset(dataset_id: str, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return _manager().validate(dataset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
