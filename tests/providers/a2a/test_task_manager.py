"""Tests for a2a/task_manager.py."""

from __future__ import annotations

import asyncio

import pytest

from keprix.providers.a2a.task_manager import Task, TaskArtifact, TaskManager, TaskStatus


@pytest.fixture
def mgr():
    return TaskManager()


@pytest.mark.asyncio
async def test_create_task(mgr):
    task = await mgr.create("Summarise report")
    assert task.id
    assert task.status == TaskStatus.PENDING
    assert task.description == "Summarise report"


@pytest.mark.asyncio
async def test_start_task(mgr):
    task = await mgr.create("Test task")
    await mgr.start(task.id, agent_id="my-agent")
    fetched = await mgr.get(task.id)
    assert fetched.status == TaskStatus.RUNNING
    assert fetched.agent_id == "my-agent"


@pytest.mark.asyncio
async def test_complete_task(mgr):
    task = await mgr.create("t")
    await mgr.start(task.id)
    await mgr.complete(task.id)
    fetched = await mgr.get(task.id)
    assert fetched.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_fail_task(mgr):
    task = await mgr.create("t")
    await mgr.start(task.id)
    await mgr.fail(task.id, "Provider error")
    fetched = await mgr.get(task.id)
    assert fetched.status == TaskStatus.FAILED
    assert fetched.error == "Provider error"


@pytest.mark.asyncio
async def test_cancel_pending_task(mgr):
    task = await mgr.create("t")
    await mgr.cancel(task.id)
    fetched = await mgr.get(task.id)
    assert fetched.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_add_artifact(mgr):
    task = await mgr.create("t")
    artifact = TaskArtifact(type="text", content="hello world")
    await mgr.add_artifact(task.id, artifact)
    fetched = await mgr.get(task.id)
    assert len(fetched.artifacts) == 1
    assert fetched.artifacts[0].content == "hello world"


@pytest.mark.asyncio
async def test_list_by_status(mgr):
    t1 = await mgr.create("a")
    t2 = await mgr.create("b")
    await mgr.start(t1.id)
    pending = await mgr.list_by_status(TaskStatus.PENDING)
    running = await mgr.list_by_status(TaskStatus.RUNNING)
    assert len(pending) == 1
    assert len(running) == 1
    assert pending[0].id == t2.id


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(mgr):
    assert await mgr.get("no-such-id") is None


@pytest.mark.asyncio
async def test_purge_completed_removes_old(mgr):
    task = await mgr.create("t")
    await mgr.complete(task.id)
    # Force old updated_at
    task = await mgr.get(task.id)
    mgr._tasks[task.id].updated_at = 0.0
    removed = await mgr.purge_completed(older_than_seconds=1)
    assert removed == 1
    assert await mgr.get(task.id) is None


@pytest.mark.asyncio
async def test_to_dict(mgr):
    task = await mgr.create("t", metadata={"key": "val"})
    d = task.to_dict()
    assert d["status"] == "pending"
    assert d["id"] == task.id
