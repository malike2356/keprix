"""Tests for SAGE researcher module."""

from __future__ import annotations

import pytest

from keprix.personas.sage.researcher import (
    MIN_SOURCES,
    Confidence,
    SageResearcher,
    StatementType,
)


@pytest.fixture
def researcher() -> SageResearcher:
    return SageResearcher(workspace_id="ws-sage", user_id="user-sage")


def _sample_sources() -> list[dict[str, str]]:
    return [
        {
            "title": "WHO Report",
            "url": "https://www.who.int/health-topic",
            "snippet": "According to research, vaccination rates increased in 2024.",
            "date": "2024-06-01",
        },
        {
            "title": "University Study",
            "url": "https://www.edu.ac.uk/study",
            "snippet": "Study found vaccination rates increased across regions.",
            "date": "2024-05-15",
        },
        {
            "title": "Reuters",
            "url": "https://www.reuters.com/health",
            "snippet": "Data shows vaccination rates increased in multiple countries.",
            "date": "2024-07-01",
        },
    ]


def test_score_source_high_for_authority(researcher: SageResearcher) -> None:
    score = researcher.score_source(_sample_sources()[0], corroboration_count=2)
    assert score.rating == Confidence.HIGH
    assert score.total >= 70


def test_classify_opinion(researcher: SageResearcher) -> None:
    assert researcher.classify_statement("I believe the market will recover") == StatementType.OPINION


def test_classify_fact(researcher: SageResearcher) -> None:
    assert researcher.classify_statement("According to the study, rates increased") == StatementType.FACT


def test_verify_claim_requires_three_sources(researcher: SageResearcher) -> None:
    sources = _sample_sources()
    verification = researcher.verify_claim("vaccination rates increased", sources)
    assert verification.verified
    assert verification.confidence == Confidence.HIGH
    assert len(verification.supporting_sources) >= MIN_SOURCES


def test_verify_opinion_not_verified_as_fact(researcher: SageResearcher) -> None:
    verification = researcher.verify_claim("I believe vaccination is effective", _sample_sources())
    assert verification.statement_type == StatementType.OPINION
    assert not verification.verified


@pytest.mark.asyncio
async def test_research_meets_minimum_sources(researcher: SageResearcher) -> None:
    result = await researcher.research("climate policy", index_to_rag=True)
    assert result.meets_source_minimum
    assert len(result.sources) >= MIN_SOURCES
    assert len(result.credibility_scores) >= MIN_SOURCES


@pytest.mark.asyncio
async def test_research_indexes_to_rag(researcher: SageResearcher) -> None:
    result = await researcher.research("renewable energy", index_to_rag=True)
    assert result.indexed_chunks > 0
    assert researcher._indexer.memory_chunks
