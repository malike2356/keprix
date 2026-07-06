"""Unit tests for deep research search and inference wiring."""

from __future__ import annotations

import json

import pytest

from keprix.research.errors import ResearchConfigError, ResearchPipelineError
from keprix.research import search as research_search


@pytest.mark.asyncio
async def test_web_search_uses_configured_provider_results(monkeypatch):
    def fake_tool(query: str, limit: int = 5) -> str:
        return json.dumps(
            {
                "success": True,
                "data": {
                    "web": [
                        {
                            "title": f"Article about {query}",
                            "url": "https://example.org/article",
                            "description": "Useful overview",
                        }
                    ]
                },
            }
        )

    monkeypatch.setattr("tools.web_tools.web_search_tool", fake_tool)
    results = await research_search.web_search("borehole drilling ghana", limit=3)
    assert len(results) == 1
    assert results[0]["url"] == "https://example.org/article"
    assert "borehole" in results[0]["title"].lower()


@pytest.mark.asyncio
async def test_web_search_raises_when_provider_not_configured(monkeypatch):
    def fake_tool(query: str, limit: int = 5) -> str:
        return json.dumps(
            {
                "success": False,
                "error": "No web search provider configured. Run `keprix tools` to set one up.",
            }
        )

    monkeypatch.setattr("tools.web_tools.web_search_tool", fake_tool)
    with pytest.raises(ResearchConfigError, match="No web search provider configured"):
        await research_search.web_search("test query")


@pytest.mark.asyncio
async def test_web_search_raises_when_no_results(monkeypatch):
    def fake_tool(query: str, limit: int = 5) -> str:
        return json.dumps({"success": True, "data": {"web": []}})

    monkeypatch.setattr("tools.web_tools.web_search_tool", fake_tool)
    with pytest.raises(ResearchPipelineError, match="No web search results"):
        await research_search.web_search("empty query")
