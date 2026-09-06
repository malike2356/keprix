"""Tests for Companies House auto-enrich (prompt 03)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from keprix.crm import companies_house_enrich as che
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def _profile(number="17103731", name="Verlox LTD"):
    return {
        "company_number": number,
        "company_name": name,
        "company_status": "active",
        "sic_codes": ["62020", "62090"],
        "registered_office_address": {"locality": "Portsmouth"},
        "officers": [{"name": "Laud Gablah", "officer_role": "director"}],
        "public_url": f"https://example.test/company/{number}",
    }


def test_match_exact_title():
    items = [
        {"company_number": "17103731", "title": "Verlox LTD", "address_snippet": "Portsmouth"},
        {"company_number": "99999999", "title": "Verlox Holdings LTD", "address_snippet": "London"},
    ]
    match = asyncio.run(che.match_company("Verlox LTD", "Portsmouth", injected_items=items))
    assert match == {"company_number": "17103731", "title": "Verlox LTD", "confidence": "high"}


def test_match_ambiguous_returns_none():
    items = [
        {"company_number": "11111111", "title": "Verlox LTD", "address_snippet": "Portsmouth"},
        {"company_number": "22222222", "title": "Verlox LTD", "address_snippet": "London"},
    ]
    # no town disambiguation when town provided matches neither uniquely -> ambiguous
    match = asyncio.run(che.match_company("Verlox LTD", "", injected_items=items))
    assert match is None
    # with town, resolves uniquely
    match = asyncio.run(che.match_company("Verlox LTD", "Portsmouth", injected_items=items))
    assert match["company_number"] == "11111111"
    assert match["confidence"] == "high"


def test_match_no_candidates_returns_none():
    match = asyncio.run(che.match_company("Nonexistent Co", injected_items=[]))
    assert match is None


def test_enrich_lead_persists(store):
    lead = store.create_lead(
        "ws1", name="Verlox LTD", company_name="Verlox LTD", locality="Portsmouth", source="fixture"
    )
    result = asyncio.run(
        che.enrich_lead(
            store,
            "ws1",
            lead["id"],
            injected_items=[
                {
                    "company_number": "17103731",
                    "title": "Verlox LTD",
                    "address_snippet": "Portsmouth",
                }
            ],
            injected_profile=_profile(),
        )
    )
    assert result["ok"] is True
    assert result["status"] == "enriched"
    updated = store.get_lead("ws1", lead["id"])
    assert updated["company_number"] == "17103731"
    assert json.loads(updated["sic_codes"]) == ["62020", "62090"]
    assert json.loads(updated["officers"])[0]["name"] == "Laud Gablah"
    assert updated["website"] == "https://example.test/company/17103731"
    assert updated["enrich_confidence"] == "high"


def test_enrich_twice_no_duplicate_and_no_website_overwrite(store):
    lead = store.create_lead(
        "ws1",
        name="Verlox LTD",
        company_name="Verlox LTD",
        locality="Portsmouth",
        website="https://existing.example",
        source="fixture",
    )
    items = [{"company_number": "17103731", "title": "Verlox LTD", "address_snippet": "Portsmouth"}]
    asyncio.run(
        che.enrich_lead(store, "ws1", lead["id"], injected_items=items, injected_profile=_profile())
    )
    asyncio.run(
        che.enrich_lead(store, "ws1", lead["id"], injected_items=items, injected_profile=_profile())
    )
    updated = store.get_lead("ws1", lead["id"])
    assert updated["website"] == "https://existing.example"  # never overwritten
    assert updated["company_number"] == "17103731"


def test_ambiguous_lead_untouched(store):
    lead = store.create_lead("ws1", name="Verlox LTD", company_name="Verlox LTD", source="fixture")
    items = [
        {"company_number": "11111111", "title": "Verlox LTD", "address_snippet": "Portsmouth"},
        {"company_number": "22222222", "title": "Verlox LTD", "address_snippet": "London"},
    ]
    result = asyncio.run(che.enrich_lead(store, "ws1", lead["id"], injected_items=items))
    assert result["status"] == "none"
    updated = store.get_lead("ws1", lead["id"])
    assert updated["enrich_confidence"] == "none"
    assert not updated["company_number"]
