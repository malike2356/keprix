"""Analytics report generator."""

from __future__ import annotations

from keprix.analytics.planner import AnalyticsPlan


def generate_report(plan: AnalyticsPlan, findings: dict, sources: list[str], methods: list[str]) -> str:
    lines = [
        "# Analytics Report",
        "",
        "## Question",
        plan.request,
        "",
        "## Data Sources",
        *[f"- {source}" for source in sources],
        "",
        "## Methods",
        *[f"- {method}" for method in methods],
        "",
        "## Findings",
    ]
    for key, value in findings.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
