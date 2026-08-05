"""Briefing and report generation for SAGE."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from keprix.compat import UTC
from pathlib import Path
from typing import Any

from keprix.playbook.runtime.graph import END, PlaybookGraph
from keprix.playbook.runtime.runner import PlaybookRunner
from keprix.personas.sage.persona import SAGE_PERSONA
from keprix.personas.sage.researcher import Confidence, MIN_SOURCES, ResearchResult, SageResearcher


@dataclass(slots=True)
class BriefSection:
    title: str
    content: str
    statement_type: str
    confidence: str
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "statement_type": self.statement_type,
            "confidence": self.confidence,
            "sources": list(self.sources),
        }


@dataclass
class BriefReport:
    topic: str
    sections: list[BriefSection] = field(default_factory=list)
    overall_confidence: str = Confidence.MEDIUM
    markdown: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "sections": [section.to_dict() for section in self.sections],
            "overall_confidence": self.overall_confidence,
            "markdown": self.markdown,
        }


class SageBriefer:
    def __init__(self, *, workspace_id: str = "default") -> None:
        self.workspace_id = workspace_id
        self.persona = SAGE_PERSONA
        self._template_path = Path(__file__).resolve().parent / "prompts" / "research_brief.md"

    def sections_from_research(self, result: ResearchResult) -> list[BriefSection]:
        researcher = SageResearcher(workspace_id=self.workspace_id)
        sections: list[BriefSection] = []

        if result.synthesis:
            sections.append(
                BriefSection(
                    title="Synthesis",
                    content=result.synthesis.split("\n", 1)[-1][:500],
                    statement_type="analysis",
                    confidence=Confidence.HIGH if result.meets_source_minimum else Confidence.LOW,
                    sources=[score.url for score in result.credibility_scores[:3]],
                )
            )

        for index, score in enumerate(result.credibility_scores[:3]):
            sections.append(
                BriefSection(
                    title=f"Source {index + 1}: {score.title}",
                    content=f"Credibility score {score.total}/100 ({score.rating})",
                    statement_type="fact",
                    confidence=score.rating,
                    sources=[score.url],
                )
            )

        for claim in result.claims:
            sections.append(
                BriefSection(
                    title="Claim verification",
                    content=claim.claim,
                    statement_type=claim.statement_type,
                    confidence=claim.confidence,
                    sources=claim.supporting_sources,
                )
            )

        if not sections:
            sections.append(
                BriefSection(
                    title="Overview",
                    content="Insufficient research data to produce a detailed brief.",
                    statement_type="analysis",
                    confidence=Confidence.LOW,
                )
            )

        return sections

    def overall_confidence(self, sections: list[BriefSection]) -> str:
        if not sections:
            return Confidence.LOW
        weights = {Confidence.HIGH: 3, Confidence.MEDIUM: 2, Confidence.LOW: 1}
        total = sum(weights.get(section.confidence, 1) for section in sections)
        average = total / len(sections)
        if average >= 2.5:
            return Confidence.HIGH
        if average >= 1.8:
            return Confidence.MEDIUM
        return Confidence.LOW

    def render_brief(self, topic: str, sections: list[BriefSection]) -> str:
        template = self._template_path.read_text(encoding="utf-8")
        overall = self.overall_confidence(sections)

        finding_rows = "\n".join(
            f"| {section.title} | {section.statement_type} | {section.confidence} | {len(section.sources)} |"
            for section in sections
        )

        source_list = "\n".join(
            f"- {url}" for section in sections for url in section.sources if url
        ) or "- No sources cited"

        consensus = "Multiple sources align on key themes." if len(sections) >= MIN_SOURCES else "Limited source overlap."
        disagreement = "Some sources use opinion language; treated separately from facts."

        bullets = "\n".join(f"- {section.title}: {section.content[:120]}" for section in sections[:5])

        replacements = {
            "{{topic}}": topic,
            "{{date}}": datetime.now(UTC).date().isoformat(),
            "{{overall_confidence}}": overall,
            "{{executive_summary}}": bullets,
            "{{finding_rows}}": finding_rows,
            "{{consensus}}": consensus,
            "{{disagreement}}": disagreement,
            "{{source_list}}": source_list,
            "{{min_sources}}": str(MIN_SOURCES),
        }
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace(key, value)
        return rendered

    def build_brief_playbook(self) -> PlaybookGraph:
        graph = PlaybookGraph("sage-brief")

        async def assemble_node(state: dict[str, Any]) -> dict[str, Any]:
            from keprix.personas.sage.researcher import ClaimVerification, SourceCredibility

            research_data = state.get("research", {})
            scores = [SourceCredibility(**row) for row in research_data.get("credibility_scores", [])]
            claims = [ClaimVerification(**row) for row in research_data.get("claims", [])]
            result = ResearchResult(
                research_id=research_data.get("research_id", "brief"),
                query=research_data.get("query", state.get("topic", "")),
                sources=research_data.get("sources", []),
                credibility_scores=scores,
                synthesis=research_data.get("synthesis", ""),
                claims=claims,
                meets_source_minimum=research_data.get("meets_source_minimum", False),
            )
            briefer = SageBriefer(workspace_id=state.get("workspace_id", "default"))
            sections = briefer.sections_from_research(result)
            state["sections"] = [section.to_dict() for section in sections]
            return state

        async def render_node(state: dict[str, Any]) -> dict[str, Any]:
            briefer = SageBriefer(workspace_id=state.get("workspace_id", "default"))
            sections = [BriefSection(**row) for row in state.get("sections", [])]
            markdown = briefer.render_brief(state.get("topic", "Research brief"), sections)
            state["brief_markdown"] = markdown
            state["overall_confidence"] = briefer.overall_confidence(sections)
            return state

        graph.add_node("assemble", assemble_node)
        graph.add_node("render", render_node)
        graph.add_edge("assemble", "render")
        graph.add_edge("render", END)
        return graph

    async def generate_brief(self, result: ResearchResult) -> BriefReport:
        graph = self.build_brief_playbook()
        runner = PlaybookRunner(graph.compile())
        run = await runner.execute_inline(
            {
                "workspace_id": self.workspace_id,
                "topic": result.query,
                "research": result.to_dict(),
            }
        )
        sections = [BriefSection(**row) for row in run.state.get("sections", [])]
        return BriefReport(
            topic=result.query,
            sections=sections,
            overall_confidence=run.state.get("overall_confidence", Confidence.MEDIUM),
            markdown=run.state.get("brief_markdown", ""),
        )
