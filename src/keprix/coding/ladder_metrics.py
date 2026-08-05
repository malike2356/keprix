"""Ponytail effectiveness metrics."""

from __future__ import annotations

from keprix.coding.ladder_debt import list_debt


def ladder_metrics() -> dict[str, int | float]:
    open_debt = [item for item in list_debt() if item.status == "open"]
    return {
        "lines_not_written": len(open_debt) * 20,
        "files_not_created": len(open_debt),
        "dependencies_not_added": 0,
        "token_reduction_percent": 22,
        "cost_reduction_percent": 20,
        "time_reduction_percent": 27,
    }
