from __future__ import annotations

import pytest

from keprix.integrations.company_registry.client import CompanyRegistryClient


@pytest.mark.asyncio
async def test_lookup_normalizes_and_merges_provider_results(monkeypatch) -> None:
    client = CompanyRegistryClient()

    async def fake_get(url, *, params=None, headers=None):
        if "opencorporates" in url:
            return {
                "results": {
                    "companies": [
                        {
                            "company": {
                                "name": "Example Inc",
                                "jurisdiction_code": "us_de",
                                "company_number": "42",
                                "company_status": "Active",
                                "opencorporates_url": "https://opencorporates.com/companies/us_de/42",
                            }
                        }
                    ]
                }
            }
        if "gleif" in url:
            return {
                "data": [
                    {
                        "id": "549300EXAMPLE",
                        "attributes": {
                            "entity": {"legalName": "Example Inc", "jurisdiction": "US-DE"},
                            "registration": {"status": "ISSUED"},
                        },
                    }
                ]
            }
        return {"0000000042": {"title": "Example Inc", "cik_str": 42}}

    monkeypatch.setattr(client, "_get", fake_get)
    monkeypatch.setenv("OPENCORPORATES_API_TOKEN", "test-token")
    result = await client.lookup("Example Inc", jurisdiction="US")
    assert result["entity"]["name"] == "Example Inc"
    assert result["entity"]["registration_id"] == "42"
    assert result["entity"]["lei"] == "549300EXAMPLE"
    assert set(result["entity"]["providers"]) == {"opencorporates", "gleif", "sec_edgar"}


@pytest.mark.asyncio
async def test_uk_routes_to_native_provider_without_global_calls(monkeypatch) -> None:
    client = CompanyRegistryClient()

    async def fail(*args, **kwargs):
        raise AssertionError("global provider should not run for UK")

    monkeypatch.setattr(client, "_get", fail)
    result = await client.lookup("Example Ltd", jurisdiction="GB")
    assert result["native_provider"] == "companies_house"
    assert result["entity"] is None
