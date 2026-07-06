"""Research job storage with disk persistence and live SSE queues."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from keprix.research.registry import ResearchTaskRecord, get_research_registry


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ResearchJob:
    id: str
    user_id: str
    query: str
    depth: str
    status: str = "running"
    sub_questions: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    report_markdown: str | None = None
    result_document_id: str | None = None
    model_used: str | None = None
    tokens_used: int = 0
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None
    events: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    _cancelled: bool = False
    workspace_id: str = "default"
    progress_pct: int = 0
    current_step: str | None = None

    @classmethod
    def from_record(cls, record: ResearchTaskRecord) -> ResearchJob:
        started = datetime.fromisoformat(record.started_at) if record.started_at else _utcnow()
        completed = (
            datetime.fromisoformat(record.completed_at) if record.completed_at else None
        )
        return cls(
            id=record.id,
            user_id=record.user_id,
            query=record.query,
            depth=record.depth,
            status=record.status,
            sub_questions=list(record.sub_questions),
            sources=list(record.sources),
            report_markdown=record.result_markdown,
            result_document_id=record.result_document_id,
            model_used=record.model,
            tokens_used=record.tokens_used,
            started_at=started,
            completed_at=completed,
            workspace_id=record.workspace_id,
            progress_pct=record.progress_pct,
            current_step=record.current_step,
            _cancelled=record.status == "cancelled",
        )

    def to_dict(self, *, include_report: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": self.id,
            "task_id": self.id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "query": self.query,
            "depth": self.depth,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "current_step": self.current_step,
            "sub_questions": self.sub_questions,
            "sources": self.sources,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_report:
            payload["report_markdown"] = self.report_markdown
        if self.result_document_id:
            payload["result_document_id"] = self.result_document_id
        return payload

    def sync_to_record(self) -> ResearchTaskRecord:
        return ResearchTaskRecord(
            id=self.id,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            query=self.query,
            depth=self.depth,
            status=self.status,
            model=self.model_used,
            progress_pct=self.progress_pct,
            current_step=self.current_step,
            result_markdown=self.report_markdown,
            result_document_id=self.result_document_id,
            error_message=None if self.status != "error" else (self.report_markdown or ""),
            sub_questions=list(self.sub_questions),
            sources=list(self.sources),
            tokens_used=self.tokens_used,
            started_at=self.started_at.isoformat(),
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            cancelled_at=_utcnow().isoformat() if self._cancelled else None,
        )


class ResearchStore:
    def __init__(self) -> None:
        self._registry = get_research_registry()
        self._live: dict[str, ResearchJob] = {}
        self._lock = asyncio.Lock()

    def _hydrate(self, record: ResearchTaskRecord) -> ResearchJob:
        live = self._live.get(record.id)
        if live is not None:
            return live
        job = ResearchJob.from_record(record)
        self._live[record.id] = job
        return job

    async def create(
        self,
        *,
        user_id: str,
        query: str,
        depth: str,
        model: str | None = None,
        workspace_id: str = "default",
    ) -> ResearchJob:
        record = self._registry.create(
            workspace_id=workspace_id,
            user_id=user_id,
            query=query,
            depth=depth,
            model=model,
        )
        job = ResearchJob.from_record(record)
        async with self._lock:
            self._live[record.id] = job
        return job

    async def get(self, job_id: str, user_id: str | None = None) -> ResearchJob | None:
        record = self._registry.get(job_id, user_id)
        if record is None:
            return None
        return self._hydrate(record)

    async def list_for_user(self, user_id: str) -> list[ResearchJob]:
        return [self._hydrate(record) for record in self._registry.list_for_user(user_id)]

    async def delete(self, job_id: str, user_id: str) -> bool:
        job = await self.get(job_id, user_id)
        if job is None:
            return False
        job._cancelled = True
        job.status = "cancelled"
        self._registry.cancel(job_id, user_id)
        async with self._lock:
            self._live.pop(job_id, None)
        return True

    async def persist(self, job: ResearchJob) -> None:
        self._registry.update(job.sync_to_record())

    async def emit(self, job: ResearchJob, event_type: str, **data: Any) -> None:
        event = {"type": event_type, **data}
        await job.events.put(event)
        self._registry.append_event(job.id, event_type, data)
        if event_type in {"source_fetched", "source_read", "sub_question_start"}:
            job.current_step = event_type.replace("_", " ")
            if event_type == "source_fetched":
                job.progress_pct = min(90, job.progress_pct + 10)
        if event_type == "complete":
            job.progress_pct = 100
        await self.persist(job)

    async def stream_events(self, job: ResearchJob) -> AsyncIterator[dict[str, Any]]:
        last_id = 0
        while True:
            for row in self._registry.list_events(job.id, since_id=last_id):
                last_id = int(row["id"])
                yield {"type": row["event_type"], **(row.get("payload") or {})}
            if job.status != "running" and job.events.empty():
                yield {"type": "complete", "status": job.status}
                break
            try:
                event = await asyncio.wait_for(job.events.get(), timeout=1.0)
                yield event
                if event.get("type") == "complete":
                    break
            except asyncio.TimeoutError:
                if job.status != "running":
                    yield {"type": "complete", "status": job.status}
                    break


_store: ResearchStore | None = None


def get_research_store() -> ResearchStore:
    global _store
    if _store is None:
        _store = ResearchStore()
    return _store
