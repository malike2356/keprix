"""Small statistical method helpers."""

from __future__ import annotations

from statistics import mean, median, pstdev


def describe(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "stddev": pstdev(values),
        "min": min(values),
        "max": max(values),
    }
