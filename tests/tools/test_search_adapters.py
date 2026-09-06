"""Prompt 56 search adapter tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from keprix.backend.tools.adapters.registry import run_adapter
from plugins.web.searxng.provider import SearXNGWebSearchProvider


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


def test_searxng_provider_sends_bearer_token(monkeypatch):
    monkeypatch.setenv("SEARXNG_URL", "https://search.verlox.uk/api")
    monkeypatch.setenv("SEARXNG_API_TOKEN", "test-token")

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"title": "Example", "url": "https://example.com", "content": "Result"}]}

    with patch("httpx.get", return_value=Response()) as request:
        result = SearXNGWebSearchProvider().search("example", limit=1)

    assert result["success"] is True
    assert request.call_args.kwargs["headers"]["Authorization"] == "Bearer test-token"
