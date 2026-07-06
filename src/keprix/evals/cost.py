"""Cost regression detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostRegression:
    detected: bool
    current_cost_usd: float
    baseline_cost_usd: float
    delta_pct: float
    message: str


def detect_cost_regression(
    current_cost_usd: float,
    baseline_cost_usd: float,
    *,
    threshold_pct: float = 10.0,
) -> CostRegression:
    if baseline_cost_usd <= 0:
        return CostRegression(
            detected=False,
            current_cost_usd=current_cost_usd,
            baseline_cost_usd=baseline_cost_usd,
            delta_pct=0.0,
            message="No baseline cost available",
        )
    delta_pct = ((current_cost_usd - baseline_cost_usd) / baseline_cost_usd) * 100.0
    detected = delta_pct > threshold_pct
    message = (
        f"Cost increased {delta_pct:.1f}% over baseline ({baseline_cost_usd:.4f} -> {current_cost_usd:.4f} USD)"
        if detected
        else f"Cost within {threshold_pct:.1f}% of baseline"
    )
    return CostRegression(
        detected=detected,
        current_cost_usd=current_cost_usd,
        baseline_cost_usd=baseline_cost_usd,
        delta_pct=delta_pct,
        message=message,
    )
