"""Tests for PRISM SEO module."""

from __future__ import annotations

import pytest

from keprix.personas.prism.seo import (
    PrismSeo,
    build_recommendations,
    contains_black_hat,
    filter_white_hat_recommendations,
    parse_html_signals,
    SeoRecommendation,
)


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Organic Growth Guide</title>
  <meta name="description" content="Learn organic growth with practical SEO steps.">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="canonical" href="https://example.com/guide">
  <script type="application/ld+json">{"@type": "Article", "headline": "Guide"}</script>
</head>
<body>
  <h1>Organic Growth Guide</h1>
  <img src="/hero.png" alt="Hero">
  <img src="/chart.png">
  <p>Content body.</p>
</body>
</html>
"""

MINIMAL_HTML = """
<html><head><title>Test</title></head><body><h1>One</h1><h2>Two</h2></body></html>
"""


@pytest.fixture
def seo() -> PrismSeo:
    return PrismSeo(workspace_id="ws-prism", user_id="user-prism")


def test_parse_html_signals_extracts_core_fields() -> None:
    signals = parse_html_signals(SAMPLE_HTML)
    assert signals["title"] == "Organic Growth Guide"
    assert "organic growth" in signals["meta_description"].lower()
    assert signals["h1_count"] == 1
    assert signals["structured_data_count"] == 1
    assert signals["viewport"]
    assert signals["images_missing_alt"] == 1


def test_build_recommendations_flags_missing_meta() -> None:
    signals = parse_html_signals("<html><body><h1>Only H1</h1></body></html>")
    recs = build_recommendations(signals, "https://example.com/page")
    categories = {rec.category for rec in recs}
    assert "On-page" in categories
    assert "Technical" in categories
    assert all(rec.impact in {"Low", "Medium", "High"} for rec in recs)
    assert all(rec.effort in {"Low", "Medium", "High"} for rec in recs)


def test_recommendations_sorted_by_priority() -> None:
    signals = parse_html_signals(MINIMAL_HTML)
    recs = build_recommendations(signals, "https://example.com/test")
    priorities = [rec.priority for rec in recs]
    assert priorities == sorted(priorities, reverse=True)


def test_black_hat_detection_and_filter() -> None:
    assert contains_black_hat("Use keyword stuffing and link schemes")
    bad = SeoRecommendation(
        category="Spam",
        change="Buy paid links from a PBN",
        why="Fast rankings",
        impact="High",
        effort="Low",
    )
    good = SeoRecommendation(
        category="On-page",
        change="Improve title tag",
        why="Better CTR",
        impact="Medium",
        effort="Low",
    )
    filtered = filter_white_hat_recommendations([bad, good])
    assert len(filtered) == 1
    assert filtered[0].change.startswith("Improve")


@pytest.mark.asyncio
async def test_audit_page_with_inline_html(seo: PrismSeo) -> None:
    report = await seo.audit_page(
        "https://example.com/guide",
        html_content=SAMPLE_HTML,
        use_browser=False,
        index_to_rag=False,
    )
    assert report.url == "https://example.com/guide"
    assert report.recommendations
    assert report.overall_health in {"Excellent", "Good", "Needs work", "Poor"}
    assert "Organic Growth Guide" in report.markdown


def test_content_brief_includes_keyword_metrics(seo: PrismSeo) -> None:
    brief = seo.build_content_brief(
        primary_keyword="local seo",
        intent="informational",
        target_url="/blog/local-seo",
        search_volume=1200,
        difficulty=42,
    )
    assert brief.primary_keyword == "local seo"
    assert brief.search_volume == 1200
    assert brief.difficulty == 42
    assert brief.outline
    assert "local seo" in brief.markdown.lower()
    assert brief.recommended_title


def test_run_render_check_uses_browser_engine(seo: PrismSeo, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSession:
        session_id = "sess-render-1"

    class FakeEngine:
        def create_session(self, **kwargs):
            return FakeSession()

        def run_action(self, session_id: str, action: str) -> dict:
            return {"status": "ok", "world": {"visible_elements": ["h1", "p"]}}

    monkeypatch.setattr("keprix.personas.prism.seo.get_action_engine", lambda: FakeEngine())
    result = seo.run_render_check("https://example.com/guide")
    assert result["session_id"] == "sess-render-1"
    assert result["rendered"] is True

