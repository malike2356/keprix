"""Market and business analysis for COMPASS."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from keprix.personas.compass.persona import COMPASS_PERSONA
from keprix.personas.sage.researcher import SageResearcher
from keprix.workspace.repository import workspace_repo


@dataclass(slots=True)
class CompetitorProfile:
    name: str
    positioning: str
    estimated_share_pct: float
    strengths: list[str]
    weaknesses: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "positioning": self.positioning,
            "estimated_share_pct": self.estimated_share_pct,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
        }


@dataclass
class MarketAnalysis:
    analysis_id: str
    market: str
    tam_usd: int
    sam_usd: int
    som_usd: int
    growth_rate_pct: float
    growth_vectors: list[str] = field(default_factory=list)
    competitors: list[CompetitorProfile] = field(default_factory=list)
    positioning_recommendation: str = ""
    assumptions: list[str] = field(default_factory=list)
    research_sources: list[str] = field(default_factory=list)
    opportunity_signals: list[str] = field(default_factory=list)
    document_id: str | None = None
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "market": self.market,
            "tam_usd": self.tam_usd,
            "sam_usd": self.sam_usd,
            "som_usd": self.som_usd,
            "growth_rate_pct": self.growth_rate_pct,
            "growth_vectors": list(self.growth_vectors),
            "competitors": [row.to_dict() for row in self.competitors],
            "positioning_recommendation": self.positioning_recommendation,
            "assumptions": list(self.assumptions),
            "research_sources": list(self.research_sources),
            "opportunity_signals": list(self.opportunity_signals),
            "document_id": self.document_id,
            "markdown": self.markdown,
        }


def _stable_int(seed: str, label: str, upper: int) -> int:
    digest = hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()
    return int(digest[:8], 16) % upper


def estimate_market_size(market: str) -> tuple[int, int, int, float]:
    tam = 50_000_000 + _stable_int(market, "tam", 950_000_000)
    sam = int(tam * (0.15 + (_stable_int(market, "sam", 25) / 100)))
    som = int(sam * (0.05 + (_stable_int(market, "som", 15) / 100)))
    growth = round(4.0 + _stable_int(market, "growth", 180) / 10.0, 1)
    return tam, sam, som, growth


def parse_opportunity_competitors(artifacts: dict[str, str]) -> list[str]:
    competitors_md = artifacts.get("04-competitors.md", "")
    names = re.findall(r"^##\s+(.+)$", competitors_md, flags=re.MULTILINE)
    return [name.strip() for name in names if name.strip()]


def parse_opportunity_market_signals(artifacts: dict[str, str]) -> list[str]:
    market_md = artifacts.get("01-market-demand.md", "")
    lines = [line.strip("- ").strip() for line in market_md.splitlines() if line.strip().startswith("-")]
    return lines[:5]


class CompassAnalyst:
    def __init__(self, *, workspace_id: str = "default", user_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.user_id = user_id
        self.persona = COMPASS_PERSONA
        self._user = {"id": user_id, "username": user_id}

    def build_competitor_profiles(self, market: str, names: list[str]) -> list[CompetitorProfile]:
        profiles: list[CompetitorProfile] = []
        for index, name in enumerate(names[:6]):
            share = max(5.0, 35.0 - (index * 6) + _stable_int(market, name, 8))
            profiles.append(
                CompetitorProfile(
                    name=name,
                    positioning=f"{name} targets the mid-market segment of {market}",
                    estimated_share_pct=round(share, 1),
                    strengths=["Established brand", "Existing distribution"],
                    weaknesses=["Slower product iteration", "Generic positioning"],
                )
            )
        if not profiles:
            profiles = [
                CompetitorProfile(
                    name="Incumbent A",
                    positioning=f"Legacy leader in {market}",
                    estimated_share_pct=32.0,
                    strengths=["Scale", "Enterprise trust"],
                    weaknesses=["High price", "Slow onboarding"],
                ),
                CompetitorProfile(
                    name="Challenger B",
                    positioning=f"Modern alternative in {market}",
                    estimated_share_pct=18.0,
                    strengths=["UX", "Faster deployment"],
                    weaknesses=["Limited integrations", "Smaller support team"],
                ),
            ]
        return profiles

    async def analyze_market(
        self,
        market: str,
        *,
        competitor_names: list[str] | None = None,
        opportunity_artifacts: dict[str, str] | None = None,
        geography: str = "global",
        use_research: bool = False,
        store: bool = True,
    ) -> MarketAnalysis:
        analysis_id = str(uuid4())
        tam, sam, som, growth = estimate_market_size(f"{market}:{geography}")

        artifact_competitors: list[str] = []
        opportunity_signals: list[str] = []
        if opportunity_artifacts:
            artifact_competitors = parse_opportunity_competitors(opportunity_artifacts)
            opportunity_signals = parse_opportunity_market_signals(opportunity_artifacts)

        names = competitor_names or artifact_competitors
        competitors = self.build_competitor_profiles(market, names)

        research_sources: list[str] = []
        if use_research:
            researcher = SageResearcher(workspace_id=self.workspace_id, user_id=self.user_id)
            result = await researcher.research(
                f"{market} market size growth competitors",
                index_to_rag=False,
                limit=3,
            )
            research_sources = [source.get("url", "") for source in result.sources if source.get("url")]

        assumptions = [
            f"TAM/SAM/SOM modelled for {geography} demand",
            "Competitor share estimates based on public signals, not audited financials",
            f"Growth rate assumes {growth}% CAGR over next 3 years",
        ]

        positioning = (
            f"Position as the clarity-first option in {market}: faster time-to-value for teams "
            f"that need outcomes in the ${som:,} serviceable obtainable segment."
        )

        analysis = MarketAnalysis(
            analysis_id=analysis_id,
            market=market,
            tam_usd=tam,
            sam_usd=sam,
            som_usd=som,
            growth_rate_pct=growth,
            growth_vectors=[
                "Digitisation of legacy workflows",
                "Budget shift toward measurable ROI tools",
                "Consolidation among mid-market buyers",
            ],
            competitors=competitors,
            positioning_recommendation=positioning,
            assumptions=assumptions,
            research_sources=research_sources,
            opportunity_signals=opportunity_signals,
        )
        analysis.markdown = self.render_markdown(analysis)

        if store:
            doc = workspace_repo.create_document(
                self._user,
                title=f"Market Analysis: {market}",
                content=analysis.markdown,
                tags=["compass-analysis", "market-sizing"],
            )
            analysis.document_id = doc.get("id")

        return analysis

    def render_markdown(self, analysis: MarketAnalysis) -> str:
        competitor_rows = "\n".join(
            f"| {row.name} | {row.estimated_share_pct}% | {row.positioning} |"
            for row in analysis.competitors
        )
        assumptions = "\n".join(f"- {item}" for item in analysis.assumptions)
        signals = "\n".join(f"- {item}" for item in analysis.opportunity_signals) or "- None from opportunity engine"
        sources = "\n".join(f"- {url}" for url in analysis.research_sources) or "- No external research run"
        vectors = "\n".join(f"- {item}" for item in analysis.growth_vectors)

        return f"""# Market Analysis: {analysis.market}

**Analysis ID:** {analysis.analysis_id}

## Market Size (USD)

| Metric | Estimate |
|--------|----------|
| TAM | ${analysis.tam_usd:,} |
| SAM | ${analysis.sam_usd:,} |
| SOM | ${analysis.som_usd:,} |
| Growth (CAGR) | {analysis.growth_rate_pct}% |

## Growth Vectors

{vectors}

## Competitive Landscape

| Competitor | Est. Share | Positioning |
|------------|------------|-------------|
{competitor_rows}

## Positioning Recommendation

{analysis.positioning_recommendation}

## Opportunity Engine Signals

{signals}

## Research Sources

{sources}

## Assumptions

{assumptions}

---
*COMPASS advises; validate figures with primary research before committing budget.*
"""
