"""Job queue concurrency tests."""

from __future__ import annotations

import uuid

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.jobs.queue import JobQueue


@pytest.fixture
def workspace_plane(tmp_path):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    return plane


def test_stale_claim_is_reclaimed(workspace_plane: WorkspaceDataPlane):
    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane
    job = queue.enqueue("data_import", {"dataset": "demo"})
    claimed = queue.claim_job(job["job_id"], worker_id="worker-stale")
    assert claimed and claimed.get("claim_token")

    with workspace_plane.connect(write=True) as conn:
        conn.execute(
            """
            UPDATE local_jobs
            SET heartbeat_at = datetime('now', '-300 seconds')
            WHERE job_id = ?
            """,
            (job["job_id"],),
        )

    reclaimed = queue.reclaim_stale(lease_seconds=120)
    assert job["job_id"] in reclaimed
    refreshed = queue.get(job["job_id"])
    assert refreshed is not None
    assert refreshed["status"] == "pending"
    assert refreshed["claim_token"] is None


def test_job_event_history_is_bounded(workspace_plane: WorkspaceDataPlane, monkeypatch):
    monkeypatch.setattr(
        "keprix.jobs.audit.get_workspace_data_plane",
        lambda workspace_id="default": workspace_plane,
    )
    from keprix.jobs.audit import append_job_event

    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane
    job = queue.enqueue("agent_task", {})
    for index in range(60):
        append_job_event(job["job_id"], f"synthetic_event_{index}")

    events = queue.list_job_events(job["job_id"], limit=50)
    assert len(events) == 50


def test_job_audit_events_persist(workspace_plane: WorkspaceDataPlane):
    queue = JobQueue(workspace_plane.workspace_id)
    queue.plane = workspace_plane
    job = queue.enqueue("statistical_analysis", {"dataset_id": "ds-1"})
    events = queue.list_job_events(job["job_id"])
    assert len(events) >= 1
    assert events[0]["event_type"] == "enqueued"
