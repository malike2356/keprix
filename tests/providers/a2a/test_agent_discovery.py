"""Tests for a2a/agent_discovery.py."""

from __future__ import annotations

import pytest

from keprix.providers.a2a.agent_discovery import AgentCard, AgentRegistry


def _card(
    agent_id="agent-1",
    name="Test Agent",
    description="Does testing stuff",
    capabilities=None,
    tags=None,
):
    return AgentCard(
        id=agent_id,
        name=name,
        description=description,
        capabilities=capabilities or ["test"],
        tags=tags or ["default"],
    )


@pytest.fixture
def registry():
    return AgentRegistry()


@pytest.mark.asyncio
async def test_register_and_get(registry):
    card = _card()
    await registry.register(card)
    fetched = await registry.get("agent-1")
    assert fetched is not None
    assert fetched.name == "Test Agent"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(registry):
    assert await registry.get("no-such") is None


@pytest.mark.asyncio
async def test_find_by_capability(registry):
    await registry.register(_card(agent_id="a", capabilities=["summarise"]))
    await registry.register(_card(agent_id="b", capabilities=["classify"]))
    results = await registry.find(capability="summarise")
    assert len(results) == 1
    assert results[0].id == "a"


@pytest.mark.asyncio
async def test_find_by_tag(registry):
    await registry.register(_card(agent_id="a", tags=["rag"]))
    await registry.register(_card(agent_id="b", tags=["coding"]))
    results = await registry.find(tag="rag")
    assert len(results) == 1 and results[0].id == "a"


@pytest.mark.asyncio
async def test_find_no_filter_returns_all(registry):
    await registry.register(_card("x"))
    await registry.register(_card("y"))
    all_agents = await registry.find()
    assert len(all_agents) == 2


@pytest.mark.asyncio
async def test_unregister_removes_agent(registry):
    await registry.register(_card())
    await registry.unregister("agent-1")
    assert await registry.get("agent-1") is None


@pytest.mark.asyncio
async def test_all_returns_all(registry):
    await registry.register(_card("a"))
    await registry.register(_card("b"))
    all_agents = await registry.all()
    assert {a.id for a in all_agents} == {"a", "b"}


@pytest.mark.asyncio
async def test_best_for_matches_keyword(registry):
    await registry.register(_card(agent_id="sum", name="Summariser", description="summarise documents"))
    await registry.register(_card(agent_id="cls", name="Classifier", description="classify emails"))
    best = await registry.best_for("summarise my report")
    assert best is not None
    assert best.id == "sum"


@pytest.mark.asyncio
async def test_best_for_empty_registry_returns_none(registry):
    result = await registry.best_for("anything")
    assert result is None


@pytest.mark.asyncio
async def test_to_dict_shape(registry):
    card = _card()
    d = card.to_dict()
    assert "id" in d and "capabilities" in d and "tags" in d
