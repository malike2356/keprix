"""Tests for SAGE briefer module."""

from __future__ import annotations

import pytest

from keprix.personas.sage.briefer import SageBriefer
from keprix.personas.sage.researcher import Confidence, ResearchResult, SageResearcher, SourceCredibility


@pytest.fixture
def briefer() -> SageBriefer:
    return SageBriefer(workspace_id="ws-sage")


@pytest.fixture
def sample_result() -> ResearchResult:
    researcher = SageResearcher()
    sources = [
        {"title": "Source A", "url": "https://www.edu.ac.uk/a", "snippet": "According to data shows growth."},
        {"title": "Source B", "url": "https://www.reuters.com/b", "snippet": "Study found growth in sector."},
        {"title": "Source C", "url": "https://www.who.int/c", "snippet": "Reported growth across regions."},
    ]
    scores = [researcher.score_source(source, corroboration_count=2) for source in sources]
    return ResearchResult(
        research_id="r1",
        query="market growth",
        sources=sources,
        credibility_scores=scores,
        synthesis=researcher.synthesize("market growth", sources, scores),
        meets_source_minimum=True,
    )


def test_sections_include_confidence(briefer: SageBriefer, sample_result: ResearchResult) -> None:
    sections = briefer.sections_from_research(sample_result)
    assert sections
    assert all(section.confidence in {Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW} for section in sections)


def test_render_brief_includes_confidence_ratings(briefer: SageBriefer, sample_result: ResearchResult) -> None:
    sections = briefer.sections_from_research(sample_result)
    markdown = briefer.render_brief(sample_result.query, sections)
    assert "Confidence" in markdown or "confidence" in markdown.lower()
    assert "market growth" in markdown
    assert "High" in markdown or "Medium" in markdown


@pytest.mark.asyncio
async def test_generate_brief_via_playbook(briefer: SageBriefer, sample_result: ResearchResult) -> None:
    brief = await briefer.generate_brief(sample_result)
    assert brief.markdown
    assert brief.overall_confidence in {Confidence.HIGH, Confidence.MEDIUM, Confidence.LOW}
    assert len(brief.sections) >= 1
