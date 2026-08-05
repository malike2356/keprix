"""Diff budget preflight gate."""

from __future__ import annotations

from typing import Any

from keprix.coding.preflight_store import PreflightGateResult


def _planned_lines(payload: dict[str, Any]) -> int:
    if payload.get("planned_lines") is not None:
        return int(payload["planned_lines"])
    plan = payload.get("mutation_plan") or {}
    if isinstance(plan, dict):
        if plan.get("planned_lines") is not None:
            return int(plan["planned_lines"])
        return int(plan.get("lines_added") or 0) + int(plan.get("lines_deleted") or 0)
    return 0


def run_diff_budget_gate(payload: dict[str, Any], *, limit: int) -> PreflightGateResult:
    planned = _planned_lines(payload)
    if planned > limit:
        return PreflightGateResult(
            "diff_budget",
            "block",
            f"Planned patch is {planned} lines, above the {limit}-line preflight budget.",
            {"planned_lines": planned, "limit": limit},
        )
    return PreflightGateResult("diff_budget", "pass", "Planned patch is within the diff budget.", {"planned_lines": planned, "limit": limit})
