"""Tests for PRISM analytics reports."""

from __future__ import annotations

from keprix.personas.prism.analytics import PrismAnalytics


def test_performance_report_includes_charts_and_trends() -> None:
    analytics = PrismAnalytics(workspace_id="ws-prism")
    report = analytics.build_performance_report(
        traffic_by_week=[120, 140, 160, 150],
        conversions_by_week=[12, 14, 18, 17],
        keyword_rankings={"primary keyword": [40, 42, 45, 48]},
        weeks=4,
    )
    payload = report.to_dict()
    assert payload["charts"]
    assert payload["trends"]
    assert payload["kpis"]
    assert payload["recommendations"]
