"""Tests for integrations/notion/workspace/context_loader.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from keprix.integrations.notion.workspace.context_loader import (
    ContextBlock,
    DatabaseQuery,
    NotionContextLoader,
)


def _page(pid="page-1", title="Test Page"):
    return {
        "id": pid,
        "properties": {
            "title": {
                "type": "title",
                "title": [{"plain_text": title}],
            }
        },
    }


def _block(btype, text):
    return {
        "type": btype,
        btype: {"rich_text": [{"plain_text": text}]},
    }


@pytest.fixture
def loader(monkeypatch):
    monkeypatch.setenv("NOTION_INTEGRATION_TOKEN", "test")
    return NotionContextLoader()


def test_extract_title_from_page(loader):
    page = _page(title="My Page")
    assert loader._extract_title(page) == "My Page"


def test_extract_title_fallback_to_id(loader):
    page = {"id": "abc123", "properties": {}}
    assert loader._extract_title(page) == "abc123"


def test_blocks_to_markdown_heading1(loader):
    blocks = [_block("heading_1", "Introduction")]
    md = loader._blocks_to_markdown(blocks)
    assert "# Introduction" in md


def test_blocks_to_markdown_heading2(loader):
    blocks = [_block("heading_2", "Section")]
    md = loader._blocks_to_markdown(blocks)
    assert "## Section" in md


def test_blocks_to_markdown_paragraph(loader):
    blocks = [_block("paragraph", "Hello world")]
    md = loader._blocks_to_markdown(blocks)
    assert "Hello world" in md


def test_blocks_to_markdown_bulleted(loader):
    blocks = [_block("bulleted_list_item", "Item one")]
    md = loader._blocks_to_markdown(blocks)
    assert "- Item one" in md


def test_blocks_to_markdown_code(loader):
    block = {
        "type": "code",
        "code": {"rich_text": [{"plain_text": "print('hi')"}], "language": "python"},
    }
    md = loader._blocks_to_markdown([block])
    assert "```python" in md
    assert "print('hi')" in md


def test_blocks_to_markdown_divider(loader):
    block = {"type": "divider", "divider": {}}
    md = loader._blocks_to_markdown([block])
    assert "---" in md


def test_page_to_summary_extracts_fields(loader):
    page = {
        "id": "x",
        "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Test"}]},
            "Status": {"type": "status", "status": {"name": "In Progress"}},
        },
    }
    summary = loader._page_to_summary(page)
    assert "Test" in summary
    assert "In Progress" in summary


@pytest.mark.asyncio
async def test_load_context_page_ids(loader):
    page = _page("p1", "Research Notes")
    blocks = [_block("paragraph", "Key finding here.")]

    with patch.object(loader, "_client") as mock_client_ctor:
        mock_client = AsyncMock()
        mock_client.get_page = AsyncMock(return_value=page)
        mock_client.list_block_children = AsyncMock(return_value={
            "results": blocks, "has_more": False
        })
        mock_client.close = AsyncMock()
        mock_client_ctor.return_value = mock_client

        result = await loader.load_context(page_ids=["p1"])

    assert len(result) == 1
    assert result[0].title == "Research Notes"
    assert "Key finding" in result[0].content


@pytest.mark.asyncio
async def test_load_context_skips_failed_pages(loader):
    with patch.object(loader, "_client") as mock_client_ctor:
        mock_client = AsyncMock()
        mock_client.get_page = AsyncMock(side_effect=Exception("not found"))
        mock_client.close = AsyncMock()
        mock_client_ctor.return_value = mock_client

        result = await loader.load_context(page_ids=["bad-id"])

    assert result == []  # failed page is silently skipped


@pytest.mark.asyncio
async def test_load_context_database_query(loader):
    db_results = {
        "results": [
            _page("r1", "Row One"),
            _page("r2", "Row Two"),
        ]
    }

    with patch.object(loader, "_client") as mock_client_ctor:
        mock_client = AsyncMock()
        mock_client.query_database = AsyncMock(return_value=db_results)
        mock_client.close = AsyncMock()
        mock_client_ctor.return_value = mock_client

        result = await loader.load_context(
            database_query=DatabaseQuery(database_id="db-123")
        )

    assert len(result) == 2
