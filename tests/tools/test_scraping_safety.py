"""Prompt 56 scraping safety tests."""

from __future__ import annotations

import pytest

from keprix.backend.tools.adapters.registry import run_adapter
from keprix.backend.tools.adapters.scraping_safety import ScrapingSafetyPolicy


def test_scraping_policy_blocks_login_hosts():
    policy = ScrapingSafetyPolicy(max_requests_per_minute=10)
    decision = policy.evaluate("https://login.example.com/page")
    assert decision.allowed is False


def test_scraping_policy_rate_limits_domain():
    policy = ScrapingSafetyPolicy(max_requests_per_minute=2)
    assert policy.evaluate("https://example.com/a").allowed is True
    assert policy.evaluate("https://example.com/b").allowed is True
    assert policy.evaluate("https://example.com/c").allowed is False


@pytest.mark.asyncio
async def test_scraping_adapter_blocks_unsafe_url(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-test")
    result = await run_adapter("firecrawl", "scrape", {"url": "https://accounts.example.com/private"}, dry_run=False)
    assert result.ok is False
    assert "blocked" in (result.error or "").lower() or "auth" in (result.error or "").lower()
