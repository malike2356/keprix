"""Tests for improvement tool gap detector."""

from __future__ import annotations

from keprix.improvement.run_analyzer import ImprovementProposal, RunAnalyzer, RunRecord
from keprix.improvement.tool_gap_detector import detect_tool_gaps


def test_detect_tool_gaps_from_failed_tool_calls() -> None:
    record = RunRecord(
        run_id="run-1",
        agent_id="demo-agent",
        ok=False,
        metadata={"task": "fetch stock price for AAPL"},
        tool_calls=[{"name": "web_search", "ok": False, "error": "timeout"}],
    )
    proposals = [
        ImprovementProposal(
            proposal_id="prop-1",
            run_id="run-1",
            agent_id="demo-agent",
            category="tool_failure",
            title="Tool failures detected",
            detail="web_search failed",
            metadata={"tools": record.tool_calls},
        )
    ]
    gaps = detect_tool_gaps(record, proposals, available_tools=["web_search"])
    assert gaps
    assert any(gap.tool_name == "web_search" for gap in gaps)


def test_detect_missing_capability_from_task() -> None:
    record = RunRecord(
        run_id="run-2",
        agent_id="demo-agent",
        ok=False,
        metadata={"task": "What is the current AAPL stock price?"},
    )
    gaps = detect_tool_gaps(record, [], available_tools=["terminal"])
    assert gaps
    assert gaps[0].tool_name == "fetch_stock_price"
