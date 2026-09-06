"""Tests for decision-maker name resolution (prompt 04)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from keprix.crm import decision_maker as dm
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_rank_role_priority():
    assert dm._rank_role("Director") < dm._rank_role("Manager")
    assert dm._rank_role("Director") < dm._rank_role("CEO")  # prompt order: director first
    assert dm._rank_role("Accountant") == len(dm.ROLE_PRIORITY)


def test_active_officers_filters_resigned():
    officers = [
        {"name": "Active Director", "officer_role": "director"},
        {"name": "Gone", "officer_role": "director", "resigned_on": "2020-01-01"},
        {"name": ""},
    ]
    active = dm._active_officers(officers)
    assert len(active) == 1
    assert active[0]["name"] == "Active Director"


def test_best_officer_ranks_director_over_manager():
    officers = [
        {"name": "Manager Bob", "officer_role": "manager"},
        {"name": "Director Alice", "officer_role": "director"},
    ]
    best = dm._best_officer(officers)
    assert best["name"] == "Director Alice"


def test_resolve_sets_name_from_officers(store):
    lead = store.create_lead("ws1", company_name="Verlox LTD", source="fixture")
    result = asyncio.run(
        dm.resolve_decision_maker(
            store,
            "ws1",
            lead["id"],
            injected_officers=[
                {"name": "Manager Bob", "officer_role": "manager"},
                {"name": "Laud Gablah", "officer_role": "director"},
            ],
        )
    )
    assert result["status"] == "resolved"
    assert result["name"] == "Laud Gablah"
    assert result["role"] == "director"
    updated = store.get_lead("ws1", lead["id"])
    assert updated["name"] == "Laud Gablah"
    assert (updated["custom_fields"] or {}).get("decision_maker", {}).get("name") == "Laud Gablah"


def test_existing_contact_name_not_overwritten(store):
    lead = store.create_lead(
        "ws1", name="Existing Person", company_name="Verlox LTD", source="fixture"
    )
    result = asyncio.run(
        dm.resolve_decision_maker(
            store,
            "ws1",
            lead["id"],
            injected_officers=[{"name": "Laud Gablah", "officer_role": "director"}],
        )
    )
    assert result["status"] == "skipped"
    updated = store.get_lead("ws1", lead["id"])
    assert updated["name"] == "Existing Person"


def test_no_officers_no_fabrication(store):
    lead = store.create_lead("ws1", company_name="Unknown Co", source="fixture")
    result = asyncio.run(
        dm.resolve_decision_maker(
            store, "ws1", lead["id"], injected_officers=[], injected_search=[]
        )
    )
    assert result["status"] == "none"
    updated = store.get_lead("ws1", lead["id"])
    assert not updated["name"]


def test_web_search_fallback(store):
    lead = store.create_lead("ws1", company_name="Acme Ltd", source="fixture")
    result = asyncio.run(
        dm.resolve_decision_maker(
            store,
            "ws1",
            lead["id"],
            injected_officers=[],
            injected_search=[{"title": "Alice Founder"}],
        )
    )
    assert result["status"] == "resolved"
    assert result["name"] == "Alice Founder"
    assert result["confidence"] == "low"
    assert result["source"] == "web_search"
