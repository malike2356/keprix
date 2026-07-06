"""Playbook download, serve, and benchmark jobs."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PlaybookJob:
    id: str
    user_id: str
    job_type: str
    model_id: str
    backend: str = "ollama"
    status: str = "pending"
    progress_pct: int = 0
    logs: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=_utcnow)
    completed_at: datetime | None = None


class PlaybookJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, PlaybookJob] = {}
        self._serving: dict[str, dict[str, Any]] = {}

    def create(
        self,
        *,
        user_id: str,
        job_type: str,
        model_id: str,
        backend: str = "ollama",
    ) -> PlaybookJob:
        job = PlaybookJob(
            id=str(uuid.uuid4()),
            user_id=user_id,
            job_type=job_type,
            model_id=model_id,
            backend=backend,
            status="running",
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str, user_id: str | None = None) -> PlaybookJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            return None
        return job

    def append_log(self, job: PlaybookJob, line: str) -> None:
        job.logs = (job.logs + line + "\n").strip()

    def list_serving(self) -> list[dict[str, Any]]:
        return list(self._serving.values())

    def register_serving(self, model_id: str, backend: str, port: int) -> None:
        self._serving[model_id] = {"model_id": model_id, "backend": backend, "port": port}

    def stop_serving(self, model_id: str) -> bool:
        return self._serving.pop(model_id, None) is not None


_store: PlaybookJobStore | None = None


def get_playbook_job_store() -> PlaybookJobStore:
    global _store
    if _store is None:
        _store = PlaybookJobStore()
    return _store


async def run_download_job(job: PlaybookJob) -> None:
    store = get_playbook_job_store()
    cmd = f"ollama pull {job.model_id}"
    store.append_log(job, f"$ {cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            store.append_log(job, text)
            if "%" in text:
                for token in text.split():
                    if token.endswith("%"):
                        try:
                            job.progress_pct = int(token.rstrip("%"))
                        except ValueError:
                            pass
        code = await proc.wait()
        if code == 0:
            job.status = "complete"
            job.progress_pct = 100
            job.result = {"ok": True}
        else:
            job.status = "failed"
            job.result = {"ok": False, "exit_code": code}
    except FileNotFoundError:
        job.status = "failed"
        store.append_log(job, "ollama not found in PATH")
        job.result = {"ok": False, "error": "ollama not installed"}
    job.completed_at = _utcnow()
