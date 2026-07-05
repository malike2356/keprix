"""Code-first analytics planner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AnalyticsPlan:
    request: str
    data_needed: list[str] = field(default_factory=list)
    code_cells: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    verification_checks: list[str] = field(default_factory=list)
    report_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request": self.request,
            "data_needed": self.data_needed,
            "code_cells": self.code_cells,
            "expected_outputs": self.expected_outputs,
            "verification_checks": self.verification_checks,
            "report_sections": self.report_sections,
        }


class AnalyticsPlanner:
    def plan(self, request: str, available_data: list[str] | None = None) -> AnalyticsPlan:
        available_data = available_data or []
        lower = request.lower()
        code = "result = {'summary': 'analysis complete'}"
        if "mean" in lower or "average" in lower:
            code = "result = {'mean': sum(values) / len(values) if values else None}"
        if "anomaly" in lower:
            code = "result = anomaly_detection(values)"
        return AnalyticsPlan(
            request=request,
            data_needed=available_data,
            code_cells=[code],
            expected_outputs=["result"],
            verification_checks=["code_safety", "result_exists"],
            report_sections=["Question", "Data Sources", "Methods", "Findings"],
        )
