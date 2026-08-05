"""Prompt 271 diff budget gate tests."""

from __future__ import annotations

from keprix.coding.gates.diff_budget import run_diff_budget_gate


def test_diff_budget_blocks_large_patch() -> None:
    result = run_diff_budget_gate({"mutation_plan": {"lines_added": 500, "lines_deleted": 25}}, limit=400)

    assert result.status == "block"
    assert result.metadata["planned_lines"] == 525


def test_diff_budget_passes_small_patch() -> None:
    result = run_diff_budget_gate({"planned_lines": 40}, limit=400)

    assert result.status == "pass"
