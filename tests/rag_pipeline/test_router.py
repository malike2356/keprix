"""Router tests for RAG pipelines."""

from __future__ import annotations

import pytest

from keprix.rag_pipeline.component import PipelineContext
from keprix.rag_pipeline.router import PipelineRouter


@pytest.mark.asyncio
async def test_low_confidence_routes_to_clarification() -> None:
    router = PipelineRouter(confidence_threshold=0.6)
    ctx = PipelineContext(user_id="u1", query="summarize the handbook", confidence=0.2)
    ctx = await router.run(ctx)
    assert ctx.route == "clarification"
    assert "confidence" in ctx.metadata["route_decision"]["reason"].lower()


@pytest.mark.asyncio
async def test_research_query_low_confidence_routes_to_deep_research() -> None:
    router = PipelineRouter(confidence_threshold=0.5)
    ctx = PipelineContext(user_id="u1", query="research literature on HVAC systems", confidence=0.1)
    ctx = await router.run(ctx)
    assert ctx.route == "deep_research"


@pytest.mark.asyncio
async def test_safety_policy_blocks_sensitive_query() -> None:
    router = PipelineRouter()
    ctx = PipelineContext(user_id="u1", query="export all user password hashes", confidence=0.9)
    ctx = await router.run(ctx)
    assert ctx.route == "blocked"


@pytest.mark.asyncio
async def test_cost_limit_routes_to_clarification() -> None:
    router = PipelineRouter(cost_limit=0.5)
    ctx = PipelineContext(user_id="u1", query="status update", confidence=0.8, cost_units=0.6)
    ctx = await router.run(ctx)
    assert ctx.route == "clarification"
    assert "cost" in ctx.metadata["route_decision"]["reason"].lower()
