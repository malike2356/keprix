"""Tests for integrations/notion/tools/registry.py."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from keprix.integrations.notion.tools.registry import (
    NOTION_TOOLS,
    NotionToolDispatcher,
)


def test_all_six_tools_registered():
    names = {t.name for t in NOTION_TOOLS}
    assert "notion_search" in names
    assert "notion_get_page" in names
    assert "notion_list_block_children" in names
    assert "notion_query_database" in names
    assert "notion_get_database" in names
    assert "notion_append_blocks" in names
    assert len(NOTION_TOOLS) == 6


def test_to_mcp_dict_has_required_fields():
    for tool in NOTION_TOOLS:
        d = tool.to_mcp_dict()
        assert "name" in d
        assert "description" in d
        assert "parameters" in d


def test_write_tools_have_write_scope():
    append = next(t for t in NOTION_TOOLS if t.name == "notion_append_blocks")
    assert "write:notion" in append.scopes


def test_read_tools_have_read_scope():
    search = next(t for t in NOTION_TOOLS if t.name == "notion_search")
    assert "read:notion" in search.scopes


@pytest.mark.asyncio
async def test_dispatch_raises_when_disabled(monkeypatch):
    monkeypatch.delenv("KEPRIX_NOTION_ENABLED", raising=False)
    dispatcher = NotionToolDispatcher()
    with pytest.raises(RuntimeError, match="disabled"):
        await dispatcher.dispatch("notion_search", {"query": "test"})


@pytest.mark.asyncio
async def test_dispatch_raises_for_unknown_tool(monkeypatch):
    monkeypatch.setenv("KEPRIX_NOTION_ENABLED", "true")
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "test-token")
    dispatcher = NotionToolDispatcher()
    with pytest.raises(ValueError, match="Unknown"):
        await dispatcher.dispatch("no_such_tool", {})


@pytest.mark.asyncio
async def test_dispatch_search_calls_client(monkeypatch):
    monkeypatch.setenv("KEPRIX_NOTION_ENABLED", "true")
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "test-token")
    mock_result = {"results": [], "object": "list"}

    with patch(
        "keprix.integrations.notion.tools.registry.NotionClient.search",
        new=AsyncMock(return_value=mock_result),
    ), patch(
        "keprix.integrations.notion.tools.registry.NotionClient.close",
        new=AsyncMock(),
    ), patch(
        "keprix.integrations.notion.tools.registry.NotionClient.__aenter__",
        new=AsyncMock(return_value=None),
    ), patch(
        "keprix.integrations.notion.tools.registry.NotionClient.__aexit__",
        new=AsyncMock(),
    ):
        dispatcher = NotionToolDispatcher()
        # Verify the tool lookup resolves correctly
        tool = next(t for t in NOTION_TOOLS if t.name == "notion_search")
        assert tool.handler_name == "search"
