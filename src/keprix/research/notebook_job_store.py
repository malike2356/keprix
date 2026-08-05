"""File-backed notebook research job storage."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from keprix_constants import get_keprix_home

NotebookSourceKind = Literal["text", "url", "file", "session_export"]
NotebookDepth = Literal["notebook", "notebook-external"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def notebook_root() -> Path:
    root = get_keprix_home() / "research" / "notebook"
    root.mkdir(parents=True, exist_ok=True)
    return root


def notebook_exports_root() -> Path:
    root = notebook_root() / "exports"
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class NotebookSource:
    id: str
    kind: NotebookSourceKind
    ref: str
    title: str
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotebookSource":
        kind = str(data.get("kind") or "text")
        if kind not in {"text", "url", "file", "session_export"}:
            kind = "text"
        return cls(
            id=str(data.get("id") or uuid4().hex[:8]),
            kind=kind,  # type: ignore[arg-type]
            ref=str(data.get("ref") or ""),
            title=str(data.get("title") or "Untitled source"),
            excerpt=data.get("excerpt"),
        )


@dataclass
class NotebookResearchJob:
    job_id: str
    depth: NotebookDepth
    sources: list[NotebookSource]
    query: str
    report_md: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    status: str = "complete"
    external_notebook_id: str | None = None
    error: str | None = None
    export_path: str | None = None
    created_at: str = field(default_factory=_now)
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sources"] = [source.to_dict() for source in self.sources]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NotebookResearchJob":
        depth = str(data.get("depth") or "notebook")
        if depth not in {"notebook", "notebook-external"}:
            depth = "notebook"
        return cls(
            job_id=str(data["job_id"]),
            depth=depth,  # type: ignore[arg-type]
            sources=[NotebookSource.from_dict(row) for row in data.get("sources") or []],
            query=str(data.get("query") or ""),
            report_md=data.get("report_md"),
            citations=list(data.get("citations") or []),
            status=str(data.get("status") or "complete"),
            external_notebook_id=data.get("external_notebook_id"),
            error=data.get("error"),
            export_path=data.get("export_path"),
            created_at=str(data.get("created_at") or _now()),
            completed_at=data.get("completed_at"),
        )


class NotebookJobStore:
    def path_for(self, job_id: str) -> Path:
        return notebook_root() / f"{job_id}.json"

    def create(
        self,
        *,
        depth: NotebookDepth,
        sources: list[NotebookSource],
        query: str,
    ) -> NotebookResearchJob:
        job = NotebookResearchJob(
            job_id=f"nb-{uuid4().hex[:10]}",
            depth=depth,
            sources=sources,
            query=query,
            status="running",
        )
        return self.save(job)

    def save(self, job: NotebookResearchJob) -> NotebookResearchJob:
        self.path_for(job.job_id).write_text(json.dumps(job.to_dict(), indent=2), encoding="utf-8")
        return job

    def get(self, job_id: str) -> NotebookResearchJob | None:
        path = self.path_for(job_id)
        if not path.is_file():
            return None
        return NotebookResearchJob.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, limit: int = 50) -> list[NotebookResearchJob]:
        paths = sorted(
            (path for path in notebook_root().glob("*.json") if path.name != "draft-sources.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return [NotebookResearchJob.from_dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths[:limit]]

    def export_markdown(self, job: NotebookResearchJob, path: str | None = None) -> Path:
        destination = Path(path).expanduser() if path else notebook_exports_root() / f"{job.job_id}.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(job.report_md or "", encoding="utf-8")
        job.export_path = str(destination)
        self.save(job)
        return destination
