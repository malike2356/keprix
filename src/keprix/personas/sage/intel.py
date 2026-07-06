"""Market intelligence and trend monitoring for SAGE."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from keprix.personas.sage.persona import SAGE_PERSONA
from keprix.personas.sage.researcher import Confidence, SageResearcher


@dataclass(slots=True)
class MonitoredSource:
    id: str
    name: str
    url: str
    source_type: str = "site"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "source_type": self.source_type,
        }


@dataclass(slots=True)
class IntelSignal:
    topic: str
    signal_type: str
    summary: str
    confidence: str
    sources: list[str] = field(default_factory=list)
    trend: str = "stable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "signal_type": self.signal_type,
            "summary": self.summary,
            "confidence": self.confidence,
            "sources": list(self.sources),
            "trend": self.trend,
        }


@dataclass
class IntelReport:
    report_id: str
    monitored_sources: list[MonitoredSource] = field(default_factory=list)
    signals: list[IntelSignal] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "monitored_sources": [source.to_dict() for source in self.monitored_sources],
            "signals": [signal.to_dict() for signal in self.signals],
            "competitors": list(self.competitors),
            "generated_at": self.generated_at,
        }


TREND_KEYWORDS: dict[str, list[str]] = {
    "growth": ["growth", "expanding", "surge", "increase", "adoption"],
    "decline": ["decline", "shrinking", "drop", "decrease", "slowdown"],
    "disruption": ["disruption", "pivot", "breakthrough", "launch", "new model"],
    "regulation": ["regulation", "compliance", "policy", "law", "gdpr"],
}


class SageIntel:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = SAGE_PERSONA
        self._sources: dict[str, MonitoredSource] = {}
        self._researcher = SageResearcher(workspace_id=workspace_id)

    def configure_sources(self, sources: list[MonitoredSource]) -> None:
        for source in sources:
            self._sources[source.id] = source

    def add_source(self, name: str, url: str, *, source_type: str = "site") -> MonitoredSource:
        source = MonitoredSource(id=str(uuid4())[:8], name=name, url=url, source_type=source_type)
        self._sources[source.id] = source
        return source

    def list_sources(self) -> list[MonitoredSource]:
        return list(self._sources.values())

    def _detect_trend(self, text: str) -> str:
        lowered = text.lower()
        scores = {trend: sum(1 for kw in keywords if kw in lowered) for trend, keywords in TREND_KEYWORDS.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "stable"

    def analyze_signals(
        self,
        *,
        topic: str,
        snippets: list[dict[str, Any]],
        competitors: list[str] | None = None,
    ) -> IntelReport:
        report_id = str(uuid4())
        signals: list[IntelSignal] = []

        for snippet in snippets:
            text = f"{snippet.get('title', '')} {snippet.get('snippet', '')} {snippet.get('excerpt', '')}"
            trend = self._detect_trend(text)
            confidence = Confidence.MEDIUM
            if any(marker in snippet.get("url", "") for marker in (".gov", ".edu")):
                confidence = Confidence.HIGH

            signals.append(
                IntelSignal(
                    topic=topic,
                    signal_type=trend,
                    summary=text[:240].strip(),
                    confidence=confidence,
                    sources=[snippet.get("url", "")],
                    trend=trend,
                )
            )

        competitor_mentions = []
        for competitor in competitors or []:
            pattern = re.compile(re.escape(competitor), re.I)
            if any(pattern.search(f"{s.get('title', '')} {s.get('snippet', '')}") for s in snippets):
                competitor_mentions.append(competitor)

        return IntelReport(
            report_id=report_id,
            monitored_sources=self.list_sources(),
            signals=signals,
            competitors=competitor_mentions,
        )

    async def run_monitoring_cycle(
        self,
        *,
        topic: str,
        competitors: list[str] | None = None,
        search_backend: str = "searxng",
    ) -> IntelReport:
        from keprix.research.search import web_search

        queries = [topic, *(f"{topic} {competitor} market" for competitor in (competitors or [])[:3])]
        snippets: list[dict[str, Any]] = []
        seen: set[str] = set()
        for query in queries:
            results = await web_search(query, backend=search_backend, limit=3)
            for result in results:
                url = result.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    snippets.append(result)

        return self.analyze_signals(topic=topic, snippets=snippets, competitors=competitors)

    def schedule_monitoring(
        self,
        *,
        topic: str,
        schedule: str = "0 8 * * 1",
        competitors: list[str] | None = None,
    ) -> dict[str, Any]:
        from keprix.cron.jobs import create_job

        prompt = (
            f"SAGE intel monitoring for workspace {self.workspace_id}. "
            f"Topic: {topic}. Competitors: {', '.join(competitors or []) or 'none'}."
        )
        job = create_job(
            prompt=prompt,
            schedule=schedule,
            name=f"sage-intel-{self.workspace_id}-{topic[:24]}",
            skill="research-intel",
            deliver="local",
        )
        return {
            "job_id": str(job.get("id", "")),
            "topic": topic,
            "schedule": schedule,
            "competitors": list(competitors or []),
            "enabled": bool(job.get("enabled", True)),
        }
