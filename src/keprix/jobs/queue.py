"""Keprix local job queue on the workspace SQLite data plane."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.data_architecture.data_plane import get_workspace_data_plane
from keprix.data_architecture.schemas import JOB_TYPES
from keprix.jobs.audit import append_job_event
from keprix.jobs.schemas import JobStatus


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobQueue:
    def __init__(self, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.plane = get_workspace_data_plane(workspace_id)

    def enqueue(self, job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if job_type not in JOB_TYPES:
            raise ValueError(f"Unsupported job type: {job_type}")
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                INSERT INTO local_jobs (
                    job_id, workspace_id, job_type, status, payload_json,
                    retry_count, consecutive_failures, max_retries, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, 0, 3, ?, ?)
                """,
                (job_id, self.workspace_id, job_type, JobStatus.PENDING, json.dumps(payload or {}), now, now),
            )
        append_job_event(job_id, "enqueued", {"job_type": job_type}, plane=self.plane)
        return self.get(job_id) or {"job_id": job_id}

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.plane.connect() as conn:
            row = conn.execute("SELECT * FROM local_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_jobs(self, *, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM local_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM local_jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def claim_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        token = secrets.token_hex(16)
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            updated = conn.execute(
                """
                UPDATE local_jobs
                SET status = ?, claim_token = ?, claimed_by = ?, claimed_at = ?, heartbeat_at = ?, updated_at = ?
                WHERE job_id = ? AND status = ?
                """,
                (JobStatus.CLAIMED, token, worker_id, now, now, now, job_id, JobStatus.PENDING),
            ).rowcount
            if updated != 1:
                return None
        append_job_event(job_id, "claimed", {"worker_id": worker_id}, plane=self.plane)
        job = self.get(job_id)
        if job:
            job["claim_token"] = token
        return job

    def claim_next(self, *, worker_id: str) -> dict[str, Any] | None:
        with self.plane.connect() as conn:
            row = conn.execute(
                "SELECT job_id FROM local_jobs WHERE status = ? ORDER BY created_at ASC LIMIT 1",
                (JobStatus.PENDING,),
            ).fetchone()
        if row is None:
            return None
        return self.claim_job(row["job_id"], worker_id=worker_id)

    def claim(self, *, worker_id: str) -> dict[str, Any] | None:
        return self.claim_next(worker_id=worker_id)

    def heartbeat(self, job_id: str, claim_token: str) -> bool:
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            updated = conn.execute(
                """
                UPDATE local_jobs SET heartbeat_at = ?, updated_at = ?
                WHERE job_id = ? AND claim_token = ? AND status IN (?, ?)
                """,
                (now, now, job_id, claim_token, JobStatus.CLAIMED, JobStatus.RUNNING),
            ).rowcount
        if updated:
            append_job_event(job_id, "heartbeat", plane=self.plane)
        return updated == 1

    def complete(self, job_id: str, claim_token: str, *, result: dict[str, Any] | None = None) -> bool:
        now = _utcnow()
        with self.plane.connect(write=True) as conn:
            updated = conn.execute(
                """
                UPDATE local_jobs SET status = ?, updated_at = ?, consecutive_failures = 0
                WHERE job_id = ? AND claim_token = ?
                """,
                (JobStatus.COMPLETED, now, job_id, claim_token),
            ).rowcount
        if updated:
            append_job_event(job_id, "completed", result or {}, plane=self.plane)
        return updated == 1

    def fail(self, job_id: str, claim_token: str, *, reason: str) -> dict[str, Any] | None:
        job = self.get(job_id)
        if job is None:
            return None
        retry_count = int(job.get("retry_count") or 0) + 1
        consecutive = int(job.get("consecutive_failures") or 0) + 1
        max_retries = int(job.get("max_retries") or 3)
        now = _utcnow()
        if retry_count >= max_retries:
            status = JobStatus.DEAD_LETTER
            append_job_event(job_id, "dead_letter", {"reason": reason}, plane=self.plane)
        else:
            status = JobStatus.PENDING
            append_job_event(job_id, "retry_scheduled", {"reason": reason, "retry_count": retry_count}, plane=self.plane)
        with self.plane.connect(write=True) as conn:
            conn.execute(
                """
                UPDATE local_jobs
                SET status = ?, retry_count = ?, consecutive_failures = ?, dead_letter_reason = ?,
                    claim_token = NULL, claimed_by = NULL, updated_at = ?
                WHERE job_id = ? AND claim_token = ?
                """,
                (
                    status,
                    retry_count,
                    consecutive,
                    reason if status == JobStatus.DEAD_LETTER else None,
                    now,
                    job_id,
                    claim_token,
                ),
            )
        return self.get(job_id)

    def list_job_events(self, job_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.plane.connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, payload_json, created_at
                FROM local_job_events
                WHERE job_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def reclaim_stale(self, *, lease_seconds: int = 120) -> list[str]:
        reclaimed: list[str] = []
        with self.plane.connect(write=True) as conn:
            rows = conn.execute(
                """
                SELECT job_id FROM local_jobs
                WHERE status IN (?, ?)
                  AND heartbeat_at IS NOT NULL
                  AND datetime(heartbeat_at) < datetime('now', ?)
                """,
                (JobStatus.CLAIMED, JobStatus.RUNNING, f"-{lease_seconds} seconds"),
            ).fetchall()
            for row in rows:
                conn.execute(
                    """
                    UPDATE local_jobs
                    SET status = ?, claim_token = NULL, claimed_by = NULL, updated_at = datetime('now')
                    WHERE job_id = ?
                    """,
                    (JobStatus.PENDING, row["job_id"]),
                )
                reclaimed.append(row["job_id"])
        for job_id in reclaimed:
            append_job_event(job_id, "stale_claim_reclaimed", plane=self.plane)
        return reclaimed

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        payload = json.loads(row["payload_json"] or "{}")
        return {
            "job_id": row["job_id"],
            "workspace_id": row["workspace_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "payload": payload,
            "claimed_by": row["claimed_by"],
            "claim_token": row["claim_token"],
            "retry_count": row["retry_count"],
            "consecutive_failures": row["consecutive_failures"],
            "dead_letter_reason": row["dead_letter_reason"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "heartbeat_at": row["heartbeat_at"],
        }


_queue: JobQueue | None = None


def get_job_queue(workspace_id: str = "default") -> JobQueue:
    global _queue
    if _queue is None or _queue.workspace_id != workspace_id:
        _queue = JobQueue(workspace_id)
    return _queue
