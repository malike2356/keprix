"""Tests for COMPASS analyst module."""

from __future__ import annotations

import pytest

from keprix.personas.compass.analyst import CompassAnalyst, estimate_market_size


@pytest.fixture
def analyst() -> CompassAnalyst:
    return CompassAnalyst(workspace_id="ws-compass", user_id="user-compass")


def test_estimate_market_size_returns_ordered_values() -> None:
    tam, sam, som, growth = estimate_market_size("workflow automation")
    assert tam > sam > som
    assert growth > 0


@pytest.mark.asyncio
async def test_analyze_market_includes_tam_sam_som(analyst: CompassAnalyst) -> None:
    analysis = await analyst.analyze_market("HR tech", store=False)
    assert analysis.tam_usd > analysis.sam_usd > analysis.som_usd
    assert analysis.growth_rate_pct > 0
    assert analysis.positioning_recommendation


@pytest.mark.asyncio
async def test_analyze_market_flags_assumptions(analyst: CompassAnalyst) -> None:
    analysis = await analyst.analyze_market("Fintech onboarding", store=False)
    assert analysis.assumptions
    assert "Assumptions" in analysis.markdown


@pytest.mark.asyncio
async def test_opportunity_artifacts_feed_competitors(analyst: CompassAnalyst) -> None:
    artifacts = {
        "04-competitors.md": "## AlphaCo\nDetails\n## BetaLabs\nMore",
        "01-market-demand.md": "- Rising demand for automation\n- Buyers prefer ROI proof",
    }
    analysis = await analyst.analyze_market(
        "Automation platforms",
        opportunity_artifacts=artifacts,
        store=False,
    )
    names = {row.name for row in analysis.competitors}
    assert "AlphaCo" in names
    assert analysis.opportunity_signals


@pytest.mark.asyncio
async def test_analyze_market_stores_workspace_document(analyst: CompassAnalyst) -> None:
    analysis = await analyst.analyze_market("Climate analytics", store=True)
    assert analysis.document_id
