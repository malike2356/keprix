"""Prompt 56 adapter registry tests."""

from __future__ import annotations

from keprix.backend.tools.adapters.registry import ALL_ADAPTERS, get_adapter, list_adapters, list_categories


def test_registry_lists_all_categories():
    categories = list_categories()
    assert categories["search"] >= 7
    assert categories["scraping"] >= 9
    assert categories["documents"] >= 8
    assert categories["databases"] >= 5
    assert categories["vector_stores"] >= 3
    assert categories["media"] >= 5
    assert categories["code_search"] >= 3
    assert categories["automation"] >= 3
    assert categories["sandboxes"] >= 2
    assert categories["evaluation"] >= 2
    assert len(ALL_ADAPTERS) == sum(categories.values())


def test_missing_dependency_returns_setup_guidance(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    adapter = get_adapter("tavily")
    assert adapter is not None
    guidance = adapter.setup_guidance()
    assert "TAVILY_API_KEY" in guidance


def test_adapter_metadata_includes_risk_and_dry_run():
    rows = list_adapters(category="automation")
    zapier = next(item for item in rows if item["name"] == "zapier")
    assert zapier["risk_level"] == "high"
    assert zapier["supports_dry_run"] is True
    assert zapier["requires_approval_for_write"] is True
