"""Tests for PRISM keywords module."""

from __future__ import annotations

import pytest

from keprix.personas.prism.keywords import KeywordIntent, PrismKeywords, classify_intent


@pytest.fixture
def keywords() -> PrismKeywords:
    return PrismKeywords(workspace_id="ws-prism")


def test_research_keywords_includes_volume_difficulty_intent(keywords: PrismKeywords) -> None:
    entries = keywords.research_keywords("content marketing", limit=8)
    assert entries
    assert len(entries) <= 8
    for entry in entries:
        assert entry.volume > 0
        assert 0 < entry.difficulty <= 100
        assert entry.intent in {
            KeywordIntent.INFORMATIONAL,
            KeywordIntent.NAVIGATIONAL,
            KeywordIntent.COMMERCIAL,
            KeywordIntent.TRANSACTIONAL,
        }


def test_classify_intent_detects_commercial() -> None:
    assert classify_intent("best crm software") == KeywordIntent.COMMERCIAL
    assert classify_intent("how to audit seo") == KeywordIntent.INFORMATIONAL
    assert classify_intent("acme login portal") == KeywordIntent.NAVIGATIONAL


def test_cluster_keywords_groups_by_theme(keywords: PrismKeywords) -> None:
    entries = keywords.research_keywords("seo audit", limit=10)
    clusters = keywords.cluster_keywords(entries)
    assert clusters
    assert clusters[0].total_volume >= clusters[-1].total_volume
    assert clusters[0].keywords
    assert clusters[0].dominant_intent


def test_gap_analysis_finds_missing_competitor_terms(keywords: PrismKeywords) -> None:
    result = keywords.gap_analysis(
        "seo tools",
        our_keywords=["seo tools", "audit checklist"],
        competitor_keywords=["seo tools", "keyword clustering", "serp analysis"],
        limit=5,
    )
    missing = {entry.keyword for entry in result.missing_keywords}
    assert "keyword clustering" in missing
    assert "seo tools" not in missing
    assert result.opportunity_score >= 0
