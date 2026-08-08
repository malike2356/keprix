"""Cancel and retry local jobs (prompt 485)."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.jobs.queue import JobQueue
from keprix.jobs.schemas import JobStatus


@pytest.fixture
def workspace_plane(tmp_path):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    return plane


def test_cancel_and_retry(workspace_plane: WorkspaceDataPlane) -> None:
    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane

    job = queue.enqueue("data_import", {"path": "x.csv"})
    cancelled = queue.cancel(job["job_id"])
    assert cancelled and cancelled["status"] == JobStatus.CANCELLED
    assert queue.cancel(job["job_id"]) is None

    dead = queue.enqueue("data_import", {"path": "y.csv"})
    claimed = queue.claim_job(dead["job_id"], worker_id="w1")
    assert claimed
    failed = queue.fail(dead["job_id"], claimed["claim_token"], reason="boom")
    while failed and failed["status"] != JobStatus.DEAD_LETTER:
        claimed = queue.claim_job(dead["job_id"], worker_id="w1")
        assert claimed
        failed = queue.fail(dead["job_id"], claimed["claim_token"], reason="boom")
    assert failed and failed["status"] == JobStatus.DEAD_LETTER
    retried = queue.retry(dead["job_id"])
    assert retried and retried["status"] == JobStatus.PENDING
