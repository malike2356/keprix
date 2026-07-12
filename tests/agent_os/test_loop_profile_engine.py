"""Prompt 261 loop profile engine tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from keprix.agent_os.hooks import record_external_run
from keprix.agent_os.loop_profile_engine import LoopProfileEngine
from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user


def _run(source_id: str, run_id: str, score: float, tokens: int = 100, corrections: list[str] | None = None) -> str:
    return record_external_run(
        source_type="playbook",
        source_id=source_id,
        run_id=run_id,
        workspace_id="default",
        status="completed",
        eval_score=score,
        tokens=tokens,
        user_corrections=corrections,
    ).entry_id


def test_baseline_capture_uses_last_successful_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    ids = [_run("daily", f"run-{index}", 0.9) for index in range(4)]

    profile = LoopProfileEngine().record_baseline("playbook", "daily", last_n=2)

    assert profile.source_id == "daily"
    assert profile.baseline_entry_ids == list(reversed(ids))[:2]


def test_eval_drop_generates_drift_proposal_and_apply_creates_draft(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    baseline = [_run("weekly", f"base-{index}", 0.95, 100) for index in range(3)]
    engine = LoopProfileEngine()
    engine.record_baseline("playbook", "weekly", baseline)
    _run("weekly", "bad-1", 0.71, 180, ["too long"])
    _run("weekly", "bad-2", 0.72, 190, ["missed CTA"])

    proposals = engine.analyze_drift("playbook", "weekly")

    categories = {proposal["category"] for proposal in proposals}
    assert "eval_drift" in categories
    assert "token_rise" in categories
    assert "user_corrections" in categories
    applied = engine.apply_proposal(proposals[0]["proposal_id"])
    assert applied is not None
    assert Path(applied["draft_path"]).exists()


def test_loop_profile_routes_emit_scout_and_apply(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.setenv("KEPRIX_AGENT_OS_ENABLED", "1")
    calls: list[dict] = []

    async def fake_emit(event_type, payload, *, workspace_id):
        calls.append({"event_type": event_type, "payload": payload, "workspace_id": workspace_id})
        return "evt_loop"

    monkeypatch.setattr("keprix.api.agent_os_ledger_routes.emit_scout_lifecycle_event", fake_emit)
    baseline = [_run("routebook", f"base-{index}", 0.9) for index in range(2)]
    _run("routebook", "weak", 0.6)
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    baseline_response = client.post("/api/agent-os/loop-profiles/playbook:routebook/baseline", json={"entry_ids": baseline})
    assert baseline_response.status_code == 200
    proposals_response = client.get("/api/agent-os/loop-profiles/playbook:routebook/proposals")
    assert proposals_response.status_code == 200
    proposals = proposals_response.json()["proposals"]
    assert proposals
    assert calls[0]["event_type"] == "loop.proposal.created"
    apply_response = client.post(f"/api/agent-os/loop-profiles/proposals/{proposals[0]['proposal_id']}/apply")
    assert apply_response.status_code == 200
    assert Path(apply_response.json()["draft_path"]).exists()
