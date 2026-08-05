"""Companies House agent tools."""

from __future__ import annotations

import json

import pytest

from keprix.tools.companies_house_tool import _handle_profile, _handle_search
from keprix.tools.registry import registry


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    monkeypatch.setenv("KEPRIX_COMPANIES_HOUSE_ENABLED", "1")


def test_tools_registered():
    assert "search:companies_house" in registry._tools
    assert "get:company_profile" in registry._tools


@pytest.mark.asyncio
async def test_search_tool_handler(monkeypatch: pytest.MonkeyPatch):
    async def _fake_search(self, query, items_per_page=20, start_index=0):
        return {"query": query, "items": [{"company_number": "123", "title": "Test"}]}

    monkeypatch.setattr(
        "keprix.integrations.companies_house.client.CompaniesHouseClient.search_companies",
        _fake_search,
    )
    raw = _handle_search({"query": "Test"})
    data = json.loads(raw)
    assert data["items"][0]["company_number"] == "123"


def test_profile_tool_handler(monkeypatch: pytest.MonkeyPatch):
    async def _fake_profile(self, company_number, include_officers=True):
        return {"company_number": company_number, "company_name": "ACME"}

    monkeypatch.setattr(
        "keprix.integrations.companies_house.client.CompaniesHouseClient.get_company_profile",
        _fake_profile,
    )
    raw = _handle_profile({"company_number": "00000006"})
    data = json.loads(raw)
    assert data["company_name"] == "ACME"
