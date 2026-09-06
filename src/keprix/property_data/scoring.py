"""Deterministic and explainable motivated-seller scoring."""

from __future__ import annotations

WEIGHTS = {"below_market": 0.4, "high_turnover": 0.35, "long_hold": 0.15, "overseas_owner": 0.1}


def score_signals(signals: list[dict]) -> dict:
    fired = []
    total = 0.0
    breakdown = {}
    for signal in signals:
        kind = str(signal.get("signal_type") or "")
        if kind not in WEIGHTS:
            continue
        strength = max(0.0, min(1.0, float(signal.get("strength") or 0)))
        contribution = WEIGHTS[kind] * strength
        breakdown[kind] = round(contribution, 6)
        total += contribution
        fired.append(kind)
    return {"score": round(min(1.0, total), 6), "signals": fired, "breakdown": breakdown}
