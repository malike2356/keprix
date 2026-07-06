"""Tests for multi-turn coding session runner."""

from __future__ import annotations

from pathlib import Path

from keprix.code_agent.session_runner import CodingSessionRunner
from keprix.code_agent.session_store import CodingSessionStore


def test_multi_turn_session_completes(tmp_path: Path) -> None:
    store = CodingSessionStore(base_dir=tmp_path)
    runner = CodingSessionRunner(store=store)
    record = runner.create_session(workspace_id="ws-run", objective="Improve test coverage")
    turn1 = runner.run_turn(record.id)
    assert turn1.ok
    assert turn1.action == "analyze"
    turn2 = runner.run_turn(record.id)
    assert turn2.ok
    turn3 = runner.run_turn(record.id)
    assert turn3.ok
    assert turn3.session_status == "completed"
    events = runner.read_trace(record.id)
    assert len(events) >= 3


def test_pause_blocks_turn(tmp_path: Path) -> None:
    store = CodingSessionStore(base_dir=tmp_path)
    runner = CodingSessionRunner(store=store)
    record = runner.create_session(workspace_id="ws-run", objective="Refactor module")
    runner.pause(record.id)
    turn = runner.run_turn(record.id)
    assert not turn.ok
    assert turn.session_status == "paused"
