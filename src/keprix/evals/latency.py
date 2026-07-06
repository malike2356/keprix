"""Latency regression detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LatencyRegression:
    detected: bool
    current_latency_ms: float
    baseline_latency_ms: float
    delta_pct: float
    message: str


def detect_latency_regression(
    current_latency_ms: float,
    baseline_latency_ms: float,
    *,
    threshold_pct: float = 15.0,
) -> LatencyRegression:
    if baseline_latency_ms <= 0:
        return LatencyRegression(
            detected=False,
            current_latency_ms=current_latency_ms,
            baseline_latency_ms=baseline_latency_ms,
            delta_pct=0.0,
            message="No baseline latency available",
        )
    delta_pct = ((current_latency_ms - baseline_latency_ms) / baseline_latency_ms) * 100.0
    detected = delta_pct > threshold_pct
    message = (
        f"Latency increased {delta_pct:.1f}% over baseline ({baseline_latency_ms:.1f} -> {current_latency_ms:.1f} ms)"
        if detected
        else f"Latency within {threshold_pct:.1f}% of baseline"
    )
    return LatencyRegression(
        detected=detected,
        current_latency_ms=current_latency_ms,
        baseline_latency_ms=baseline_latency_ms,
        delta_pct=delta_pct,
        message=message,
    )
