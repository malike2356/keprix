"""Filesystem store for video ingest manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from keprix_constants import get_keprix_home


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def video_ingest_root() -> Path:
    root = get_keprix_home() / "ingest" / "video"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class VideoIngestJob:
    job_id: str
    source_type: str
    source_ref: str
    mode: str
    transcript_text: str | None = None
    transcript_path: str | None = None
    frames: list[dict[str, Any]] = field(default_factory=list)
    manifest_path: str = ""
    created_at: str = field(default_factory=_now)
    status: str = "pending"
    error: str | None = None
    local_source_path: str | None = None
    vault_copy_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VideoIngestJob":
        return cls(
            job_id=str(data["job_id"]),
            source_type=str(data.get("source_type") or "local"),
            source_ref=str(data.get("source_ref") or ""),
            mode=str(data.get("mode") or "caption-only"),
            transcript_text=data.get("transcript_text"),
            transcript_path=data.get("transcript_path"),
            frames=list(data.get("frames") or []),
            manifest_path=str(data.get("manifest_path") or ""),
            created_at=str(data.get("created_at") or _now()),
            status=str(data.get("status") or "pending"),
            error=data.get("error"),
            local_source_path=data.get("local_source_path"),
            vault_copy_path=data.get("vault_copy_path"),
        )


class VideoJobStore:
    def job_dir(self, job_id: str) -> Path:
        path = video_ingest_root() / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def manifest_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "manifest.json"

    def create(self, *, source_type: str, source_ref: str, mode: str) -> VideoIngestJob:
        job_id = uuid4().hex[:12]
        job = VideoIngestJob(
            job_id=job_id,
            source_type=source_type,
            source_ref=source_ref,
            mode=mode,
            manifest_path=str(self.manifest_path(job_id)),
        )
        return self.save(job)

    def save(self, job: VideoIngestJob) -> VideoIngestJob:
        if not job.manifest_path:
            job.manifest_path = str(self.manifest_path(job.job_id))
        Path(job.manifest_path).write_text(json.dumps(job.to_dict(), indent=2), encoding="utf-8")
        return job

    def get(self, job_id: str) -> VideoIngestJob | None:
        path = self.manifest_path(job_id)
        if not path.is_file():
            return None
        return VideoIngestJob.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 50) -> list[VideoIngestJob]:
        manifests = sorted(video_ingest_root().glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [VideoIngestJob.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in manifests[:limit]]
