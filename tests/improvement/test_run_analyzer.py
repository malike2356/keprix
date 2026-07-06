"""Tests for failed run improvement proposals and eval backfill."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.improvement.eval_backfill import list_eval_cases, proposal_to_eval_case, save_eval_case
from keprix.improvement.run_analyzer import RunAnalyzer, RunRecord


@pytest.fixture
def analyzer_dirs(tmp_path: Path, monkeypatch) -> Path:
    runs = tmp_path / "runs"
    proposals = tmp_path / "proposals"
    eval_cases = tmp_path / "eval_cases"
    runs.mkdir()
    proposals.mkdir()
    eval_cases.mkdir()
    monkeypatch.setattr("keprix.improvement.run_analyzer._runs_dir", lambda: runs)
    monkeypatch.setattr("keprix.improvement.run_analyzer._proposals_dir", lambda: proposals)
    monkeypatch.setattr("keprix.improvement.eval_backfill._eval_dir", lambda: eval_cases)
    return tmp_path


def test_failed_run_creates_improvement_proposal(analyzer_dirs: Path) -> None:
    analyzer = RunAnalyzer()
    record = RunRecord(
        run_id="failed-run",
        agent_id="demo-agent",
        ok=False,
        steps=[{"name": "tool_call", "duration_ms": 8000}],
        tool_calls=[{"name": "terminal", "ok": False, "error": "exit 1", "duration_ms": 1200}],
        eval_score=0.4,
        cost_usd=1.5,
        user_corrections=["Use the tests folder, not src"],
        metadata={"task": "fix failing tests", "message": "fix failing tests"},
    )
    analyzer.save_run(record)
    proposals = analyzer.analyze(record)
    assert proposals
    categories = {proposal.category for proposal in proposals}
    assert "repeated_failure" in categories
    assert "tool_failure" in categories
    assert "slow_step" in categories
    assert "high_cost" in categories
    assert "user_correction" in categories
    assert "low_eval" in categories
    assert all(proposal.status == "pending_approval" for proposal in proposals)


def test_proposal_can_become_eval_case(analyzer_dirs: Path) -> None:
    analyzer = RunAnalyzer()
    record = RunRecord(
        run_id="failed-run-2",
        agent_id="demo-agent",
        ok=False,
        metadata={"task": "summarize logs"},
    )
    proposals = analyzer.analyze(record)
    case = proposal_to_eval_case(record, proposals[0])
    save_eval_case(case)
    loaded = list_eval_cases(proposal_id=proposals[0].proposal_id)
    assert loaded
    assert loaded[0].source_run_id == record.run_id
