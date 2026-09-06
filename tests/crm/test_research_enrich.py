"""Tests for deep-research contact enrichment (prompt 02)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from keprix.crm import research_enrich as re
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def _fixture_lead(store):
    return store.create_lead(
        "ws1",
        name="Ada Lovelace",
        emails=[{"address": "ada@analytical.engine", "primary": True}],
        company_name="Analytical Engines Ltd",
        source="fixture",
    )


def test_split_name():
    assert re.split_name("Ada Lovelace") == ("Ada", "Lovelace")
    assert re.split_name("Madonna") == ("Madonna", "")
    assert re.split_name("") == ("", "")
    assert re.split_name("Jean-Luc Picard") == ("Jean-Luc", "Picard")


def test_domain_from_email_free_mail():
    assert re.domain_from_email("ada@gmail.com") == ""
    assert re.domain_from_email("bob@yahoo.co.uk") == ""
    assert re.domain_from_email("carol@outlook.com") == ""


def test_domain_from_email_business():
    assert re.domain_from_email("ada@analytical.engine") == "analytical.engine"
    assert re.domain_from_email("ADA@Acme.Co.UK") == "acme.co.uk"


def test_company_from_domain():
    assert re.company_from_domain("acme.co.uk") == "Acme"
    assert re.company_from_domain("") == ""
    assert re.company_from_domain("foo-bar.co.uk") == "Foo Bar"


def test_research_resolves_business_lead(store):
    lead = _fixture_lead(store)
    ch_profile = {
        "company_number": "01234567",
        "company_name": "Analytical Engines Ltd",
        "company_status": "active",
        "sic_codes": ["62020"],
        "registered_office_address": {"locality": "London"},
        "public_url": "https://example.test/company/01234567",
        "officers": [{"name": "Ada Lovelace", "officer_role": "director"}],
    }
    search_results = [
        {
            "title": "Ada Lovelace",
            "url": "https://analytical.engine",
            "snippet": "Mathematician linkedin.com/in/adalovelace",
        }
    ]
    result = asyncio.run(
        re.research_lead(
            store,
            "ws1",
            lead["id"],
            search_results=search_results,
            companies_house_profile=ch_profile,
        )
    )
    assert result["ok"] is True
    updated = store.get_lead("ws1", lead["id"])
    assert updated["first_name"] == "Ada"
    assert updated["last_name"] == "Lovelace"
    assert updated["website"] == "https://analytical.engine"
    assert updated["linkedin_url"] == "https://linkedin.com/in/adalovelace"
    assert updated["company_number"] == "01234567"
    assert (updated["custom_fields"] or {}).get("companies_house", {}).get(
        "company_number"
    ) == "01234567"
    assert updated["research_status"] == "done"


def test_free_mail_capture_stays_partial(store):
    lead = store.create_lead(
        "ws1",
        name="Mystery Person",
        emails=[{"address": "mystery@gmail.com", "primary": True}],
        source="capture",
    )
    result = asyncio.run(
        re.research_lead(store, "ws1", lead["id"], search_results=[], companies_house_profile=None)
    )
    assert result["ok"] is True
    updated = store.get_lead("ws1", lead["id"])
    assert updated["research_status"] == "partial"
    assert updated["company_name"] in (None, "")
    assert updated["company_number"] in (None, "")
    assert not updated["website"]


def test_fill_empty_only_never_overwrites(store):
    lead = _fixture_lead(store)
    store.update_lead("ws1", lead["id"], website="https://existing.example")
    ch_profile = {
        "company_number": "01234567",
        "company_name": "Analytical Engines Ltd",
        "public_url": "https://example.test/company/01234567",
        "sic_codes": ["62020"],
        "registered_office_address": {"locality": "London"},
    }
    asyncio.run(
        re.research_lead(
            store, "ws1", lead["id"], search_results=[], companies_house_profile=ch_profile
        )
    )
    updated = store.get_lead("ws1", lead["id"])
    assert updated["website"] == "https://existing.example"  # not overwritten


def test_batch_reports_counts(store):
    a = _fixture_lead(store)
    b = store.create_lead(
        "ws1",
        name="Free Person",
        emails=[{"address": "free@gmail.com", "primary": True}],
        source="capture",
    )
    result = asyncio.run(re.research_leads_batch(store, "ws1", [a["id"], b["id"], "missing-id"]))
    assert result["ok"] is True
    assert result["done"] >= 0
    assert result["skipped"] == 1  # missing-id
