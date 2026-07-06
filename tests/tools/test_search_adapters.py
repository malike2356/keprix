"""Prompt 56 search adapter tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from keprix.backend.tools.adapters.registry import run_adapter


@pytest.mark.asyncio
async def test_search_adapter_returns_citations(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    fake = {
        "results": [
            {"title": "Python", "url": "https://docs.python.org", "content": "Official docs", "score": 0.9}
        ]
    }
    with patch("plugins.web.tavily.provider._tavily_request", return_value=fake):
        result = await run_adapter(
            "tavily",
            "search",
            {"query": "python docs"},
            dry_run=False,
            approved=True,
        )
    assert result.ok is True
    assert len(result.citations) == 1
    assert result.citations[0].url == "https://docs.python.org"


@pytest.mark.asyncio
async def test_search_adapter_setup_guidance_without_env(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = await run_adapter("tavily", "search", {"query": "hello"})
    assert result.ok is False
    assert result.setup_guidance
    assert "TAVILY_API_KEY" in result.setup_guidance
