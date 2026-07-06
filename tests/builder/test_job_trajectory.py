"""Builder job trajectory API tests (Prompt 198)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from keprix.api.main import app
from keprix.backend.builder.store import get_builder_store, reset_builder_store
from keprix.coding.trajectory import TrajectoryLogger
from keprix.coding.trajectory_steps import events_to_patch_steps


@pytest.fixture
def builder_store(tmp_path, monkeypatch):
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    reset_builder_store()
    return get_builder_store()


@pytest.fixture
def trajectory_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("keprix.coding.trajectory._trajectory_dir", lambda: tmp_path)
    return tmp_path


def test_patch_steps_include_diff(trajectory_dir) -> None:
    logger = TrajectoryLogger()
    logger.log("issue_parsed", {"title": "Fix header"})
    logger.log(
        "patch_proposed",
        {"patch": "--- a/README.md\n+++ b/README.md\n@@\n+fix\n", "edit_count": 1},
    )
    steps = events_to_patch_steps(logger.read_events())
    assert len(steps) == 2
    assert steps[1]["diff"]
    assert "README.md" in steps[1]["diff"]


@pytest.mark.asyncio
async def test_builder_job_detail_includes_trajectory(builder_store, trajectory_dir) -> None:
    logger = TrajectoryLogger()
    logger.log("issue_parsed", {"title": "Add feature"})
    logger.log("patch_proposed", {"patch": "--- a/app.py\n+++ b/app.py\n@@\n+print('ok')\n", "edit_count": 1})

    job = builder_store.create_job(
        {
            "project_id": "proj-1",
            "job_type": "add-feature",
            "instruction": "Add logging",
        }
    )
    builder_store.update_job(
        job["id"],
        {
            "status": "done",
            "trajectory_run_id": logger.run_id,
            "needs_tier3_approval": False,
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/builder/jobs/{job['id']}")

    assert response.status_code == 200
    body = response.json()
    assert len(body["trajectory"]) >= 2
    assert any(step.get("diff") for step in body["trajectory"])
    assert body["job"]["trajectory_run_id"] == logger.run_id


@pytest.mark.asyncio
async def test_builder_job_marks_approval_step(builder_store, trajectory_dir) -> None:
    logger = TrajectoryLogger()
    logger.log("patch_proposed", {"patch": "--- a/x.py\n+++ b/x.py\n@@\n+blocked\n", "edit_count": 1})
    logger.log(
        "approval_required",
        {"reason": "human review required", "patch": "--- a/x.py\n+++ b/x.py\n@@\n+blocked\n", "needs_approval": True},
    )

    job = builder_store.create_job(
        {
            "project_id": "proj-1",
            "job_type": "add-feature",
            "instruction": "Risky patch",
        }
    )
    builder_store.update_job(
        job["id"],
        {
            "status": "failed",
            "trajectory_run_id": logger.run_id,
            "needs_tier3_approval": True,
            "approval_reason": "human review required",
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/builder/jobs/{job['id']}")

    body = response.json()
    assert body["job"]["needs_tier3_approval"] is True
    approval_steps = [step for step in body["trajectory"] if step["needs_approval"]]
    assert approval_steps
