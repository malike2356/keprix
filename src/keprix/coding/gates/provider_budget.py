"""Provider budget preflight gate."""

from __future__ import annotations

from typing import Any

from keprix.coding.preflight_store import PreflightGateResult


def run_provider_budget_gate(payload: dict[str, Any], *, warn_pct: int) -> PreflightGateResult:
    usage_pct = payload.get("provider_budget_pct")
    if usage_pct is None:
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        used = usage.get("used")
        limit = usage.get("limit")
        usage_pct = (float(used) / float(limit) * 100) if used is not None and limit else 0
    usage_pct = float(usage_pct or 0)
    if usage_pct >= warn_pct:
        return PreflightGateResult(
            "provider_budget",
            "warn",
            f"Provider budget is at {usage_pct:.0f}%; consider a cheaper model profile.",
            {"usage_pct": usage_pct, "warn_pct": warn_pct},
        )
    return PreflightGateResult("provider_budget", "pass", "Provider budget is below warning threshold.", {"usage_pct": usage_pct, "warn_pct": warn_pct})
