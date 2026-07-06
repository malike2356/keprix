"""Agent migration HTTP routes (Prompt 42)."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.backend.migration.adapters import parse_source
from keprix.backend.migration.importer import MigrationImporter
from keprix.backend.migration.manifest import AgentMigrationManifest
from keprix.backend.migration.store import get_migration_history_store

router = APIRouter(prefix="/api/migration", tags=["migration"])


class ValidateBody(BaseModel):
    manifest: dict[str, Any]


class ApplyBody(BaseModel):
    manifest: dict[str, Any]
    approved_item_ids: list[str] = Field(default_factory=list)
    workspace_id: str = "default"


def _extract_upload(upload: UploadFile, dest: Path) -> None:
    suffix = Path(upload.filename or "upload.zip").suffix.lower()
    raw = upload.file.read()
    if suffix == ".zip":
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(tmp_path, "r") as archive:
                archive.extractall(dest)
        finally:
            tmp_path.unlink(missing_ok=True)
        return
    if suffix == ".json":
        (dest / "manifest.json").write_bytes(raw)
        return
    raise ValueError("Upload must be a .zip export directory or .json manifest")


@router.post("/parse")
async def parse_migration(
    source: str = Form(...),
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if source not in {"hermes", "openclaw", "markdown", "generic"}:
        raise HTTPException(status_code=422, detail=f"Unsupported source: {source}")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            _extract_upload(file, root)
            manifest = parse_source(source, root)
        except (ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return manifest.model_dump(mode="json")


@router.post("/validate")
async def validate_migration(body: ValidateBody, _user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        manifest = AgentMigrationManifest.model_validate(body.manifest)
    except Exception as exc:
        return {"valid": False, "errors": [str(exc)]}
    errors = manifest.validate_integrity()
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/apply")
async def apply_migration(body: ApplyBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    try:
        manifest = AgentMigrationManifest.model_validate(body.manifest)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user_id = str(user.get("id") or user.get("username") or "default")
    importer = MigrationImporter()
    result = await importer.apply(
        manifest,
        body.approved_item_ids,
        workspace_id=body.workspace_id,
        user_id=user_id,
    )
    return result.model_dump()


@router.get("/history")
async def migration_history(
    workspace_id: str | None = None,
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    rows = get_migration_history_store().list_history(workspace_id)
    return {"items": rows, "count": len(rows)}
