"""Tests for persistent research registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.research.registry import ResearchTaskRegistry, TASK_ID_RE


@pytest.fixture()
def registry(tmp_path: Path) -> ResearchTaskRegistry:
    return ResearchTaskRegistry(base_dir=tmp_path)


def test_create_generates_rsch_id(registry: ResearchTaskRegistry) -> None:
    task = registry.create(
        workspace_id="default",
        user_id="user-1",
        query="test query",
        depth="quick",
    )
    assert TASK_ID_RE.fullmatch(task.id)
    assert registry.get(task.id, "user-1") is not None


def test_events_replay_since_id(registry: ResearchTaskRegistry) -> None:
    task = registry.create(
        workspace_id="default",
        user_id="user-1",
        query="events",
        depth="standard",
    )
    first = registry.append_event(task.id, "step_start", {"step": "a"})
    registry.append_event(task.id, "source_fetched", {"count": 1})
    events = registry.list_events(task.id, since_id=first)
    assert len(events) == 1
    assert events[0]["event_type"] == "source_fetched"


def test_persistence_across_instances(tmp_path: Path) -> None:
    reg1 = ResearchTaskRegistry(base_dir=tmp_path)
    task = reg1.create(
        workspace_id="default",
        user_id="u",
        query="persist",
        depth="deep",
    )
    reg2 = ResearchTaskRegistry(base_dir=tmp_path)
    loaded = reg2.get(task.id, "u")
    assert loaded is not None
    assert loaded.query == "persist"


def test_purge_expired_removes_old_tasks(tmp_path) -> None:
    from datetime import datetime, timedelta, timezone

    registry = ResearchTaskRegistry(base_dir=tmp_path)
    task = registry.create(
        workspace_id="default",
        user_id="user-1",
        query="old",
        depth="quick",
    )
    task.expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    registry.update(task)
    assert registry.purge_expired() == 1
    assert registry.get(task.id, "user-1") is None


def test_invalid_task_id_returns_none() -> None:
    registry = ResearchTaskRegistry()
    assert registry.get("bad-id", "user-1") is None
