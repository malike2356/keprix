"""Duplicate task preflight gate."""

from __future__ import annotations

import re
from typing import Any

from keprix.coding.preflight_store import PreflightGateResult


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def run_duplicate_task_gate(payload: dict[str, Any], *, window_turns: int) -> PreflightGateResult:
    intent = _normalize(str(payload.get("intent") or payload.get("issue") or ""))
    recent = [_normalize(str(item)) for item in (payload.get("recent_user_messages") or [])[-window_turns:]]
    if intent and intent in recent:
        return PreflightGateResult(
            "duplicate_task",
            "warn",
            "A matching task appears in the recent session window.",
            {"window_turns": window_turns},
        )
    return PreflightGateResult("duplicate_task", "pass", "No duplicate task found in recent turns.", {"window_turns": window_turns})
