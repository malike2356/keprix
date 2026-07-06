"""Integration smoke test for long-horizon coding sessions."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.code_agent.session_runner import CodingSessionRunner
from keprix.code_agent.session_store import CodingSessionStore


@pytest.mark.asyncio
async def test_long_horizon_coding_pause_resume(tmp_path: Path) -> None:
    store = CodingSessionStore(base_dir=tmp_path / "sessions")
    runner = CodingSessionRunner(store=store)
    record = runner.create_session(workspace_id="ws-smoke", objective="Add health endpoint")
    first = runner.run_turn(record.id)
    runner.pause(record.id)
    blocked = runner.run_turn(record.id, user_input="continue")
    assert blocked.session_status == "paused"
    runner.resume(record.id)
    second = runner.run_turn(record.id, user_input="continue")
    assert second.ok
    assert second.turn >= first.turn + 1
