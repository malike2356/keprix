"""Video ingest API routes."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.ingest.video_ingest_service import VideoIngestService, video_ingest_enabled
from keprix.ingest.video_job_store import video_ingest_root

router = APIRouter(prefix="/api/ingest/video", tags=["ingest"])


class VideoIngestBody(BaseModel):
    source: str = Field(..., min_length=1)
    mode: str = Field(default="balanced", pattern="^(caption-only|sparse|balanced|dense)$")
    copy_to_vault: bool = False
    sparse_minutes: int = Field(default=5, ge=1, le=120)
    dense_interval_sec: int = Field(default=30, ge=1, le=3600)
    max_frames: int | None = Field(default=None, ge=1, le=100)


def _guard_enabled() -> None:
    if not video_ingest_enabled():
        raise HTTPException(status_code=403, detail="Video ingest is disabled")


@router.post("")
async def ingest_video(body: VideoIngestBody, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    try:
        job = VideoIngestService().ingest(
            body.source,
            mode=body.mode,
            copy_to_vault=body.copy_to_vault,
            sparse_minutes=body.sparse_minutes,
            dense_interval_sec=body.dense_interval_sec,
            max_frames=body.max_frames,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job.to_dict()}


@router.post("/upload")
async def upload_and_ingest_video(
    user: dict = Depends(get_current_user),
    file: UploadFile = File(...),
    mode: str = Form(default="balanced"),
    copy_to_vault: bool = Form(default=False),
) -> dict[str, Any]:
    """Accept a local video upload, save under ingest uploads, then run ingest."""
    _guard_enabled()
    _ = user
    if mode not in {"caption-only", "sparse", "balanced", "dense"}:
        raise HTTPException(status_code=400, detail="Invalid frame mode")
    filename = Path(file.filename or "upload.bin").name
    upload_dir = video_ingest_root() / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(filename).stem or "upload"
    suffix = Path(filename).suffix or ".bin"
    target = upload_dir / f"{stem}{suffix}"
    counter = 0
    while target.exists():
        counter += 1
        target = upload_dir / f"{stem}-{counter}{suffix}"
    try:
        with target.open("wb") as handle:
            shutil.copyfileobj(file.file, handle)
    finally:
        await file.close()
    try:
        job = VideoIngestService().ingest(
            str(target),
            mode=mode,
            copy_to_vault=copy_to_vault,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job.to_dict(), "saved_path": str(target)}


@router.get("")
async def list_video_ingests(limit: int = 50, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    return {"jobs": [job.to_dict() for job in VideoIngestService().store.list(limit=limit)]}


@router.get("/{job_id}")
async def get_video_ingest(job_id: str, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    _guard_enabled()
    _ = user
    job = VideoIngestService().store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="video ingest job not found")
    return {"job": job.to_dict()}


@router.get("/{job_id}/frames/{index}")
async def get_video_frame(
    job_id: str,
    index: int,
    user: dict = Depends(get_current_user),
) -> FileResponse:
    _guard_enabled()
    _ = user
    if index < 0:
        raise HTTPException(status_code=400, detail="Invalid frame index")
    job = VideoIngestService().store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="video ingest job not found")
    if index >= len(job.frames):
        raise HTTPException(status_code=404, detail="frame not found")
    frame_path = Path(str(job.frames[index].get("path") or ""))
    if not frame_path.is_file():
        raise HTTPException(status_code=404, detail="frame file missing")
    return FileResponse(frame_path)
