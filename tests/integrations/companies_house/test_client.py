"""Companies House client and config tests (mocked HTTP)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from keprix.integrations.companies_house.client import CompaniesHouseClient
from keprix.integrations.companies_house.config import ensure_egress_allowlist, status_payload
from keprix.integrations.companies_house.errors import CompaniesHouseConfigError
from keprix.security.egress_policy import get_egress_policy, reset_egress_policy


class _FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload) if not isinstance(payload, str) else payload

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self._responses:
            raise AssertionError("No more fake responses")
        return self._responses.pop(0)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    monkeypatch.setenv("KEPRIX_COMPANIES_HOUSE_ENABLED", "1")
    reset_egress_policy()
    yield
    reset_egress_policy()


@pytest.mark.asyncio
async def test_search_companies_maps_hits(monkeypatch: pytest.MonkeyPatch):
    fake = _FakeClient(
        [
            _FakeResponse(
                200,
                {
                    "total_results": 1,
                    "items_per_page": 20,
                    "start_index": 0,
                    "items": [
                        {
                            "company_number": "00000006",
                            "title": "EXAMPLE LTD",
                            "company_status": "active",
                            "company_type": "ltd",
                            "date_of_creation": "1862-01-01",
                            "address_snippet": "London",
                        }
                    ],
                },
            )
        ]
    )
    monkeypatch.setattr(
        "keprix.http_client.get_http_client",
        lambda **kwargs: fake,
    )
    result = await CompaniesHouseClient().search_companies("example")
    assert result["total_results"] == 1
    assert result["items"][0]["company_number"] == "00000006"
    assert "find-and-update.company-information.service.gov.uk/company/00000006" in (
        result["items"][0]["public_url"] or ""
    )
    auth = fake.calls[0]["auth"]
    assert isinstance(auth, httpx.BasicAuth)
    assert auth._auth_header == httpx.BasicAuth("test-key", "")._auth_header


@pytest.mark.asyncio
async def test_profile_includes_officers(monkeypatch: pytest.MonkeyPatch):
    fake = _FakeClient(
        [
            _FakeResponse(
                200,
                {
                    "company_number": "00000006",
                    "company_name": "EXAMPLE LTD",
                    "company_status": "active",
                    "type": "ltd",
                    "sic_codes": ["62012"],
                    "registered_office_address": {
                        "address_line_1": "1 Test Street",
                        "locality": "London",
                        "postal_code": "E1 1AA",
                        "country": "United Kingdom",
                    },
                },
            ),
            _FakeResponse(
                200,
                {
                    "items": [
                        {
                            "name": "SMITH, Jane",
                            "officer_role": "director",
                            "appointed_on": "2020-01-01",
                        }
                    ]
                },
            ),
        ]
    )
    monkeypatch.setattr("keprix.http_client.get_http_client", lambda **kwargs: fake)
    profile = await CompaniesHouseClient().get_company_profile("00000006")
    assert profile["company_name"] == "EXAMPLE LTD"
    assert profile["sic_codes"] == ["62012"]
    assert profile["officers"][0]["name"] == "SMITH, Jane"
    assert profile["registered_office_address"]["formatted"]


@pytest.mark.asyncio
async def test_missing_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    with pytest.raises(CompaniesHouseConfigError, match="API key"):
        await CompaniesHouseClient().search_companies("x")


def test_status_and_egress_allowlist():
    payload = status_payload()
    assert payload["configured"] is True
    ensure_egress_allowlist("keprix")
    hosts = get_egress_policy().snapshot()["keprix"]["allowed_hosts"]
    assert "api.company-information.service.gov.uk" in hosts
