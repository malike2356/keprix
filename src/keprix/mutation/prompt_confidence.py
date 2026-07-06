"""Confidence estimation for prompt improvements (Prompt 152)."""

from __future__ import annotations


def estimate_confidence(category: str) -> float:
    mapping = {
        "user_correction": 0.90,
        "low_eval": 0.70,
        "repeated_failure": 0.80,
    }
    return mapping.get(category, 0.70)
