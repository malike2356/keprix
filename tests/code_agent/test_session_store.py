"""Tests for long-horizon coding session store."""

from __future__ import annotations

from pathlib import Path

from keprix.code_agent.session_store import CodingSessionStore


def test_create_and_load_session(tmp_path: Path) -> None:
    store = CodingSessionStore(base_dir=tmp_path)
    record = store.create(workspace_id="ws-code", objective="Fix login bug", repo_path="/tmp/repo")
    loaded = store.get(record.id)
    assert loaded is not None
    assert loaded.objective == "Fix login bug"
    assert loaded.status == "active"
    assert loaded.trajectory_run_id


def test_list_sessions_by_status(tmp_path: Path) -> None:
    store = CodingSessionStore(base_dir=tmp_path)
    record = store.create(workspace_id="ws-code", objective="Task A")
    record.status = "paused"
    store.save(record)
    paused = store.list_sessions(status="paused")
    assert len(paused) == 1
