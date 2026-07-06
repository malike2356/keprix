"""Workspace image gallery routes."""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from keprix.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/workspace/gallery", tags=["workspace-gallery"])


def _gallery_dir() -> Path:
    base = Path(os.environ.get("KEPRIX_DATA_DIR", "/tmp/keprix-data"))
    path = base / "gallery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_id(user: dict) -> str:
    return str(user.get("id") or user.get("username") or "local")


def _item_meta(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "id": path.stem,
        "filename": path.name,
        "url": f"/api/workspace/gallery/{path.stem}/file",
        "size_bytes": stat.st_size,
        "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


@router.get("")
async def list_gallery(_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    items = []
    for path in sorted(_gallery_dir().glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            items.append(_item_meta(path))
    return {"items": items}


@router.post("/upload")
async def upload_gallery_image(
    file: UploadFile = File(...),
    _user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")
    suffix = Path(file.filename or "upload.png").suffix or ".png"
    image_id = uuid.uuid4().hex
    dest = _gallery_dir() / f"{image_id}{suffix}"
    with dest.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)
    return {"item": _item_meta(dest)}


@router.get("/{image_id}/file")
async def get_gallery_file(image_id: str, _user: dict = Depends(get_current_user)) -> FileResponse:
    for path in _gallery_dir().glob(f"{image_id}.*"):
        if path.is_file():
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="Image not found")


@router.delete("/{image_id}")
async def delete_gallery_image(image_id: str, _user: dict = Depends(get_current_user)) -> dict[str, bool]:
    removed = False
    for path in _gallery_dir().glob(f"{image_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)
            removed = True
    if not removed:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"ok": True}
