"""Traffic and ranking analytics reports for PRISM."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from keprix.compat import UTC
from typing import Any

from keprix.personas.prism.persona import PRISM_PERSONA


@dataclass(slots=True)
class ChartSpec:
    chart_id: str
    chart_type: str
    title: str
    labels: list[str]
    series: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "chart_type": self.chart_type,
            "title": self.title,
            "labels": list(self.labels),
            "series": list(self.series),
        }


@dataclass
class PerformanceReport:
    report_id: str
    period_start: str
    period_end: str
    summary: str
    kpis: dict[str, Any] = field(default_factory=dict)
    charts: list[ChartSpec] = field(default_factory=list)
    trends: dict[str, str] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "summary": self.summary,
            "kpis": self.kpis,
            "charts": [chart.to_dict() for chart in self.charts],
            "trends": self.trends,
            "recommendations": list(self.recommendations),
            "workspace_payload": self.to_workspace_payload(),
        }

    def to_workspace_payload(self) -> dict[str, Any]:
        return {
            "charts": [chart.to_dict() for chart in self.charts],
            "tables": [
                {
                    "name": "kpi_summary",
                    "rows": [{"metric": key, "value": value} for key, value in self.kpis.items()],
                }
            ],
        }


def _trend_label(current: float, previous: float) -> str:
    if previous <= 0:
        return "flat"
    delta = ((current - previous) / previous) * 100
    if delta >= 5:
        return "up"
    if delta <= -5:
        return "down"
    return "flat"


class PrismAnalytics:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = PRISM_PERSONA

    def build_performance_report(
        self,
        *,
        keyword_rankings: dict[str, list[int]] | None = None,
        traffic_by_week: list[int] | None = None,
        conversions_by_week: list[int] | None = None,
        weeks: int = 8,
    ) -> PerformanceReport:
        from uuid import uuid4

        end = datetime.now(UTC).date()
        start = end - timedelta(weeks=weeks - 1)
        labels = [(start + timedelta(weeks=offset)).isoformat() for offset in range(weeks)]

        traffic = traffic_by_week or [900 + (index * 45) + (index % 3) * 20 for index in range(weeks)]
        conversions = conversions_by_week or [max(8, value // 25) for value in traffic]
        rankings = keyword_rankings or {
            "primary keyword": [28, 24, 22, 19, 17, 15, 14, 13],
            "supporting keyword": [45, 42, 40, 38, 35, 33, 31, 30],
        }

        avg_position = sum(rankings["primary keyword"]) / len(rankings["primary keyword"])
        organic_sessions = sum(traffic)
        conversion_rate = (sum(conversions) / organic_sessions) * 100 if organic_sessions else 0.0

        traffic_trend = _trend_label(traffic[-1], traffic[-2] if len(traffic) > 1 else traffic[-1])
        current_position = rankings["primary keyword"][-1]
        previous_position = (
            rankings["primary keyword"][-2]
            if len(rankings["primary keyword"]) > 1
            else rankings["primary keyword"][-1]
        )
        if current_position < previous_position:
            ranking_trend = "up"
        elif current_position > previous_position:
            ranking_trend = "down"
        else:
            ranking_trend = "flat"

        charts = [
            ChartSpec(
                chart_id="organic-traffic",
                chart_type="line",
                title="Organic sessions by week",
                labels=labels,
                series=[{"name": "Sessions", "data": traffic}],
            ),
            ChartSpec(
                chart_id="avg-position",
                chart_type="line",
                title="Average keyword position (primary)",
                labels=labels,
                series=[{"name": "Position", "data": rankings["primary keyword"]}],
            ),
            ChartSpec(
                chart_id="conversions",
                chart_type="bar",
                title="Organic conversions by week",
                labels=labels,
                series=[{"name": "Conversions", "data": conversions}],
            ),
        ]

        recommendations = [
            "Refresh top landing page meta descriptions to lift CTR on page-one terms.",
            "Publish one supporting article targeting gap keywords identified this period.",
            "Double down on LinkedIn posts tied to pages gaining impressions.",
        ]

        summary = (
            f"Organic sessions: {organic_sessions:,} over {weeks} weeks; "
            f"avg position {avg_position:.1f}; conversion rate {conversion_rate:.2f}%."
        )

        return PerformanceReport(
            report_id=str(uuid4()),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            summary=summary,
            kpis={
                "organic_sessions": organic_sessions,
                "avg_position": round(avg_position, 1),
                "conversion_rate_pct": round(conversion_rate, 2),
                "keywords_tracked": len(rankings),
            },
            charts=charts,
            trends={
                "traffic": traffic_trend,
                "rankings": ranking_trend,
                "conversions": _trend_label(conversions[-1], conversions[-2] if len(conversions) > 1 else conversions[-1]),
            },
            recommendations=recommendations,
        )
