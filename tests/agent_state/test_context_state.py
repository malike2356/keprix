"""Unit tests for durable agent context state files."""

from __future__ import annotations

import json

from keprix.agent_state.context_state import ContextStateStore


def test_create_read_update_atomic_json(tmp_path):
    store = ContextStateStore(root=tmp_path)
    state = store.create_state_file(
        "sess-1",
        "Build feature X",
        steps=["Design", "Implement", "Test"],
        constraints=["No secrets in logs"],
        decisions=["Use Postgres"],
    )
    assert len(state.pending) == 3
    assert state.constraints[0].text == "No secrets in logs"

    path = store.state_path("sess-1")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["session_id"] == "sess-1"
    assert "completed" in raw and "pending" in raw

    store.update_state_file(
        "sess-1",
        step_id="step-001",
        status="completed",
        output="Design done",
        decision="Use FastAPI",
    )
    resumed = store.resume("sess-1")
    assert resumed["last_completed_step_id"] == "step-001"
    assert resumed["next_step"]["id"] == "step-002"
    assert any(d["text"] == "Use FastAPI" for d in resumed["state"]["decisions"])


def test_format_for_injection_resume(tmp_path):
    store = ContextStateStore(root=tmp_path)
    store.create_state_file("s2", "Long job", steps=["A", "B"])
    store.update_state_file("s2", step_id="step-001", status="completed", output="ok")
    text = store.format_for_injection("s2")
    assert text is not None
    assert "Resume at: step-002" in text
    assert "Last completed: step-001" in text
