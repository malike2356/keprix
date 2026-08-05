"""Tests for workspace discovery state (Prompt 277 - home page shell backend)."""

from __future__ import annotations

import pytest

from keprix.workspace.discovery_state import (
    DiscoveryState,
    DiscoveryStateStore,
    get_discovery_store,
    reset_discovery_store,
)
from keprix.workspace.greeting import get_greeting, get_suggestion_chips


# ------------------------------------------------------------------ greeting

@pytest.mark.parametrize("hour,expected_prefix", [
    (0, "Working late"),
    (4, "Working late"),
    (5, "Good morning"),
    (11, "Good morning"),
    (12, "Good afternoon"),
    (17, "Good afternoon"),
    (18, "Good evening"),
    (21, "Good evening"),
    (22, "Working late"),
    (23, "Working late"),
])
def test_get_greeting_by_hour(hour: int, expected_prefix: str):
    assert get_greeting(hour) == expected_prefix


def test_suggestion_chips_keprix():
    chips = get_suggestion_chips("keprix")
    assert len(chips) >= 3
    assert all(isinstance(c, str) for c in chips)


def test_suggestion_chips_aiva_differ_from_keprix():
    assert get_suggestion_chips("aiva") != get_suggestion_chips("keprix")


def test_suggestion_chips_abbis_differ_from_keprix():
    assert get_suggestion_chips("abbis") != get_suggestion_chips("keprix")


def test_suggestion_chips_unknown_surface_falls_back_to_keprix():
    assert get_suggestion_chips("unknown_product") == get_suggestion_chips("keprix")


# ------------------------------------------------------------------ discovery state

def test_discovery_state_to_dict_keys():
    state = DiscoveryState()
    d = state.to_dict()
    assert "quotaUsagePct" in d
    assert "brainHealthScore" in d
    assert "memoryCount" in d
    assert "brainGraphVisited" in d
    assert "sessionCount" in d
    assert "skillCount" in d
    assert "completedTaskCount" in d
    assert "playbookCount" in d
    assert "voiceProvisioned" in d
    assert "workspaceAgeDays" in d


def test_discovery_state_defaults():
    state = DiscoveryState()
    assert state.quota_usage_pct is None
    assert state.memory_count == 0
    assert state.brain_graph_visited is False
    assert state.voice_provisioned is False


# ------------------------------------------------------------------ discovery store

@pytest.fixture(autouse=True)
def reset_store():
    reset_discovery_store()
    yield
    reset_discovery_store()


@pytest.mark.asyncio
async def test_brain_graph_not_visited_by_default():
    store = DiscoveryStateStore()
    assert not await store.is_brain_graph_visited("ws-1")


@pytest.mark.asyncio
async def test_mark_brain_graph_visited():
    store = DiscoveryStateStore()
    await store.mark_brain_graph_visited("ws-1")
    assert await store.is_brain_graph_visited("ws-1")


@pytest.mark.asyncio
async def test_brain_graph_visited_is_per_workspace():
    store = DiscoveryStateStore()
    await store.mark_brain_graph_visited("ws-1")
    assert not await store.is_brain_graph_visited("ws-2")


@pytest.mark.asyncio
async def test_acted_on_empty_by_default():
    store = DiscoveryStateStore()
    assert await store.get_acted_on_ids("ws-1") == set()


@pytest.mark.asyncio
async def test_mark_acted_on_records_trigger():
    store = DiscoveryStateStore()
    await store.mark_acted_on("ws-1", "quota_warning", 1_700_000_000)
    ids = await store.get_acted_on_ids("ws-1")
    assert "quota_warning" in ids


@pytest.mark.asyncio
async def test_acted_on_is_per_workspace():
    store = DiscoveryStateStore()
    await store.mark_acted_on("ws-1", "quota_warning", 1_700_000_000)
    assert await store.get_acted_on_ids("ws-2") == set()


@pytest.mark.asyncio
async def test_multiple_triggers_can_be_acted_on():
    store = DiscoveryStateStore()
    await store.mark_acted_on("ws-1", "quota_warning", 1_700_000_000)
    await store.mark_acted_on("ws-1", "brain_discovery", 1_700_000_001)
    ids = await store.get_acted_on_ids("ws-1")
    assert "quota_warning" in ids
    assert "brain_discovery" in ids


@pytest.mark.asyncio
async def test_get_discovery_store_singleton():
    reset_discovery_store()
    s1 = get_discovery_store()
    s2 = get_discovery_store()
    assert s1 is s2


# ------------------------------------------------------------------ discovery API

@pytest.mark.asyncio
async def test_discovery_route_get_returns_dict():
    from keprix.api.discovery_routes import get_discovery_state
    result = await get_discovery_state(workspace_id="ws-test")
    assert isinstance(result, dict)
    assert "sessionCount" in result
    assert "actedOnTriggerIds" in result


@pytest.mark.asyncio
async def test_discovery_route_patch_acted_on():
    from keprix.api.discovery_routes import patch_discovery_state, ActOnRequest

    req = ActOnRequest(trigger_id="quota_warning", action="acted_on")
    result = await patch_discovery_state(req, workspace_id="ws-test")
    assert result["ok"] is True
    assert result["trigger_id"] == "quota_warning"


@pytest.mark.asyncio
async def test_discovery_route_patch_brain_graph_visited():
    from keprix.api.discovery_routes import patch_discovery_state, get_discovery_state, ActOnRequest

    req = ActOnRequest(trigger_id="", action="brain_graph_visited")
    await patch_discovery_state(req, workspace_id="ws-visit")
    state = await get_discovery_state(workspace_id="ws-visit")
    assert state["brainGraphVisited"] is True


@pytest.mark.asyncio
async def test_discovery_route_patch_unknown_action_returns_error():
    from keprix.api.discovery_routes import patch_discovery_state, ActOnRequest

    req = ActOnRequest(trigger_id="x", action="unknown_action")
    result = await patch_discovery_state(req, workspace_id="ws-err")
    assert result["ok"] is False
    assert "error" in result
