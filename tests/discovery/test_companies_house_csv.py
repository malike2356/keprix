"""Companies House + CSV discovery tests (prompt 437)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from keprix.crm.store import reset_crm_store_for_tests
from keprix.discovery import (
    DiscoverLimits,
    DiscoverQuery,
    get_discovery_runner,
    reset_discovery_registry_for_tests,
)
from keprix.discovery.adapters.companies_house import CompaniesHouseAdapter
from keprix.discovery.adapters.csv_import import CsvDiscoveryAdapter
from keprix.outreach.ops import OutreachOpsStore
from keprix.outreach.store import reset_outreach_store_for_tests


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    reset_outreach_store_for_tests(tmp_path / "outreach.sqlite")
    import keprix.outreach.ops as ops_mod

    ops_mod._ops = OutreachOpsStore(path=tmp_path / "outreach.sqlite")
    monkeypatch.setenv("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "0")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "0")
    reset_discovery_registry_for_tests()
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_companies_house_maps_mocked_search(monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "test-key")
    monkeypatch.setenv("KEPRIX_COMPANIES_HOUSE_ENABLED", "1")
    payload = {
        "items": [
            {
                "company_number": "12345678",
                "title": "ACME PLUMBING LTD",
                "company_status": "active",
                "address_snippet": "1 High St, Manchester",
                "date_of_creation": "2018-01-01",
                "public_url": "https://find-and-update.company-information.service.gov.uk/company/12345678",
            },
            {
                "company_number": "87654321",
                "title": "CLOSED CO",
                "company_status": "dissolved",
                "address_snippet": None,
                "date_of_creation": "2024-01-01",
            },
        ]
    }

    async def _search(*_a, **_k):
        return payload

    with patch(
        "keprix.integrations.companies_house.client.CompaniesHouseClient.search_companies",
        new=AsyncMock(side_effect=_search),
    ):
        adapter = CompaniesHouseAdapter()
        cands = adapter.discover(
            DiscoverQuery(text="acme", params={"location": "Manchester", "status": "active"}),
            DiscoverLimits(max_results=20),
        )
    assert len(cands) == 1
    assert cands[0].company_number == "12345678"
    assert cands[0].source == "companies_house"
    assert cands[0].score_hint and cands[0].score_hint >= 0.7


def test_csv_fifty_rows_to_list(store):
    rows = [
        {
            "company": f"Co {i}",
            "email": f"c{i}@example.com",
            "phone": f"+44100000{i:02d}",
        }
        for i in range(50)
    ]
    adapter = CsvDiscoveryAdapter()
    cands = adapter.discover(
        DiscoverQuery(params={"rows": rows}),
        DiscoverLimits(max_results=50),
    )
    assert len(cands) == 50

    runner = get_discovery_runner(store=store)
    job = runner.create_job(
        "ws_a",
        "csv",
        params={"rows": rows},
        list_name="CSV50",
        auto_materialize=True,
    )
    result = runner.run_job("ws_a", job["id"], materialize=True, force=True)
    assert result["materialize"]["member_count"] == 50
    members = store.list_memberships("ws_a", result["materialize"]["list_id"])
    assert len(members) == 50


def test_csv_dedupe_reuses_existing_lead(store):
    store.upsert_lead(
        "ws_a",
        name="Existing",
        company_name="Dupe Co",
        emails=[{"address": "dupe@example.com", "primary": True}],
        external_source_id="dupe@example.com",
        source="prior",
    )
    rows = [{"company": "Dupe Co", "email": "dupe@example.com"}]
    runner = get_discovery_runner(store=store)
    job = runner.create_job("ws_a", "csv", params={"rows": rows}, auto_materialize=True)
    result = runner.run_job("ws_a", job["id"], materialize=True, force=True)
    assert result["materialize"]["reused"] >= 1


def test_discovery_run_tool_deep_links(store, monkeypatch):
    monkeypatch.setenv("KEPRIX_DISCOVERY_SOFT_WALL_MATERIALIZE", "0")
    import json

    from keprix.tools import crm_tools

    raw = crm_tools.discovery_run(
        {
            "workspace_id": "ws_a",
            "adapter": "fake",
            "query": "ToolCo",
            "materialize": True,
            "force": True,
        }
    )
    payload = json.loads(raw)
    assert "deep_links" in payload
    assert payload["deep_links"]["job"].startswith("/crm/jobs/")
