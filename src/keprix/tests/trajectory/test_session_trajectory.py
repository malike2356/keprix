"""Tests for append-only session trajectory (prompt 770)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from keprix.trajectory.redaction import redact_payload
from keprix.trajectory.service import TrajectoryService, reset_trajectory_service_for_tests
from keprix.trajectory.store import AppendOnlyViolation


ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def svc(tmp_path):
    return reset_trajectory_service_for_tests(sqlite_path=tmp_path / "traj.db")


def test_append_only_rejects_in_place_update(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1", title="t1")
    event = svc.append(traj["trajectory_id"], "message", {"text": "hello"})
    with pytest.raises(AppendOnlyViolation):
        svc.store.update_event(event.event_id, payload={"text": "mutated"})
    with pytest.raises(AppendOnlyViolation):
        svc.store.delete_event(event.event_id)
    # Original intact
    events = svc.store.list_events(traj["trajectory_id"])
    assert len(events) == 1
    assert events[0].payload["text"] == "hello"


def test_search_filters(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1")
    tid = traj["trajectory_id"]
    svc.append(tid, "tool_call", {"args": {}}, tool_name="terminal")
    svc.append(tid, "tool_result", {"output": "ok"}, tool_name="terminal")
    svc.record_soft_wall(tid, outcome="denied", tool_name="terminal", detail={"reason": "hardline"})
    svc.record_mutation(tid, stage="propose", detail={"kind": "mount"}, error_text="boom fail")
    svc.append(tid, "error", {"msg": "loop"}, error_text="agent failure xyz")

    by_type = svc.search(trajectory_id=tid, event_type="soft_wall")
    assert len(by_type) == 1
    assert by_type[0]["soft_wall_outcome"] == "denied"

    by_tool = svc.search(trajectory_id=tid, tool_name="terminal")
    assert len(by_tool) >= 2

    by_sw = svc.search(trajectory_id=tid, soft_wall_outcome="denied")
    assert len(by_sw) == 1

    by_err = svc.search(trajectory_id=tid, error_query="failure")
    assert any("failure" in (e.get("error_text") or "") for e in by_err)

    mut = svc.search(trajectory_id=tid, event_type="mutation")
    assert len(mut) == 1
    assert mut[0]["payload"]["stage"] == "propose"


def test_fork_preserves_prefix_and_diverges(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1", title="parent")
    tid = traj["trajectory_id"]
    svc.append(tid, "message", {"text": "a"})
    svc.append(tid, "tool_call", {"name": "x"}, tool_name="memory")
    svc.append(tid, "tool_result", {"ok": True}, tool_name="memory")
    child = svc.fork(tid, through_seq=2, title="child-fork")
    assert child["forked_event_count"] == 2
    assert child["parent_trajectory_id"] == tid

    child_events = svc.store.list_events(child["trajectory_id"])
    assert [e.seq for e in child_events] == [1, 2]
    assert child_events[0].payload["text"] == "a"

    # Parent continues independently
    svc.append(tid, "note", {"text": "parent-only"})
    svc.append(child["trajectory_id"], "note", {"text": "child-only"})
    parent_events = svc.store.list_events(tid)
    child_events2 = svc.store.list_events(child["trajectory_id"])
    assert parent_events[-1].payload["text"] == "parent-only"
    assert child_events2[-1].payload["text"] == "child-only"
    assert len(parent_events) == 4
    assert len(child_events2) == 3


def test_replay_recorded_does_not_execute_live_tools(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1")
    tid = traj["trajectory_id"]
    svc.append(tid, "tool_call", {"command": "rm -rf /"}, tool_name="terminal")
    svc.append(
        tid,
        "tool_result",
        {"output": "blocked", "returncode": 126},
        tool_name="terminal",
    )
    svc.record_soft_wall(tid, outcome="denied", tool_name="terminal")
    replay = svc.replay(tid, mode="recorded")
    assert replay["mode"] == "recorded"
    assert replay["step_count"] == 3
    assert all(step.get("execute") is False for step in replay["steps"])
    assert all(step.get("use_recorded_result") for step in replay["steps"])

    live = svc.replay(tid, mode="live")
    dangerous = [s for s in live["steps"] if s.get("tool_name") == "terminal" and s["event_type"] == "tool_call"]
    assert dangerous
    assert dangerous[0].get("requires_soft_wall") is True


def test_secrets_redacted_on_append(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1")
    tid = traj["trajectory_id"]
    event = svc.append(
        tid,
        "message",
        {
            "api_key": "sk-live-SHOULD_NOT_PERSIST_1234567890",
            "password": "hunter2",
            "note": "safe text",
            "nested": {"token": "abc123secret"},
        },
    )
    assert event.payload["api_key"] == "[redacted]"
    assert event.payload["password"] == "[redacted]"
    assert event.payload["note"] == "safe text"
    assert event.payload["nested"]["token"] == "[redacted]"

    # Also redact free-form token-ish strings in text
    redacted = redact_payload({"text": "Authorization: Bearer sk-live-ABCDEFGHIJKLMNOPQRST"})
    assert "[redacted]" in str(redacted)


def test_export_fixture_hook_for_772(svc: TrajectoryService):
    traj = svc.create(workspace_id="ws1")
    tid = traj["trajectory_id"]
    svc.append(tid, "checkpoint", {"label": "start"})
    exported = svc.store.export_events_for_fixture(tid)
    assert len(exported) == 1
    assert exported[0]["event_type"] == "checkpoint"


def test_trajectory_page_exists():
    page = ROOT / "frontend" / "src" / "app" / "(workspace)" / "trajectory" / "page.tsx"
    assert page.is_file()
    text = page.read_text(encoding="utf-8")
    assert "trajectory-page" in text
    assert "Fork" in text
    assert "Replay" in text


def test_no_cordis_or_dsh_dependency():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = [str(d).lower() for d in pyproject.get("project", {}).get("dependencies", [])]
    for dep in deps:
        assert "cordis" not in dep
        assert "deepseek-harness" not in dep
