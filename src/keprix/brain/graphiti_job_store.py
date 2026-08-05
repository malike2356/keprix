"""File-backed Graphiti ingest job store."""

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


def jobs_root() -> Path:
    path = get_keprix_home() / "brain" / "graphiti" / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class GraphitiIngestJob:
    source_type: str
    source_ref: str
    status: str = "queued"
    nodes_added: int = 0
    edges_added: int = 0
    graphiti_episode_id: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=_now)
    job_id: str = field(default_factory=lambda: uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphitiIngestJob":
        return cls(
            job_id=str(data["job_id"]),
            source_type=str(data["source_type"]),
            source_ref=str(data["source_ref"]),
            status=str(data.get("status") or "queued"),
            nodes_added=int(data.get("nodes_added") or 0),
            edges_added=int(data.get("edges_added") or 0),
            graphiti_episode_id=data.get("graphiti_episode_id"),
            error=data.get("error"),
            created_at=str(data.get("created_at") or _now()),
        )


class GraphitiJobStore:
    def save(self, job: GraphitiIngestJob) -> GraphitiIngestJob:
        (jobs_root() / f"{job.job_id}.json").write_text(json.dumps(job.to_dict(), indent=2), encoding="utf-8")
        return job

    def get(self, job_id: str) -> GraphitiIngestJob | None:
        path = jobs_root() / f"{job_id}.json"
        if not path.is_file():
            return None
        return GraphitiIngestJob.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 50) -> list[GraphitiIngestJob]:
        paths = sorted(jobs_root().glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        return [GraphitiIngestJob.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths[:limit]]
