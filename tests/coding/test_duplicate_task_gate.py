"""Prompt 271 duplicate-task gate tests."""

from __future__ import annotations

from keprix.coding.gates.duplicate_task import run_duplicate_task_gate


def test_duplicate_task_warns_within_window() -> None:
    result = run_duplicate_task_gate(
        {
            "intent": "Add billing export",
            "recent_user_messages": ["Review auth", "Add billing export"],
        },
        window_turns=8,
    )

    assert result.status == "warn"
    assert result.gate == "duplicate_task"


def test_duplicate_task_passes_outside_window() -> None:
    result = run_duplicate_task_gate(
        {
            "intent": "Add billing export",
            "recent_user_messages": ["Add billing export", "Review auth", "Update docs"],
        },
        window_turns=2,
    )

    assert result.status == "pass"
