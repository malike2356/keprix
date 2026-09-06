"""Tests for A/B auto-attribution + ICP auto-rescore (prompt 09)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.crm import ab_attribution as ab
from keprix.crm.store import reset_crm_store_for_tests


@pytest.fixture()
def store(tmp_path: Path):
    return reset_crm_store_for_tests(tmp_path / "crm.sqlite")


def test_rescore_unchanged_without_icp(store):
    lead = store.create_lead("ws1", name="Acme", company_name="Acme Ltd", source="fixture")
    result = ab.rescore_after_enrichment(store, "ws1", lead["id"], reason="research_enrich")
    assert result["ok"] is True
    assert result["status"] == "unchanged"
    assert result["reason"] == "no_active_icp"


def test_rescore_logs_delta(store):
    from keprix.crm.icp import activate_icp, create_icp

    icp = create_icp(
        store, "ws1", name="Property", keywords=["letting"], include_rules=["letting agent"]
    )
    activate_icp(store, "ws1", icp["id"], force=True)
    lead = store.create_lead("ws1", name="Acme", company_name="Acme Lettings Ltd", source="fixture")
    # first score establishes baseline
    result = ab.rescore_after_enrichment(store, "ws1", lead["id"], reason="research_enrich")
    assert result["ok"] is True
    assert result["status"] == "rescored"
    assert result["new"] >= 15  # keyword hit


def test_rescore_unchanged_when_score_stable(store):
    from keprix.crm.icp import activate_icp, create_icp

    icp = create_icp(store, "ws1", name="Property", keywords=["letting"])
    activate_icp(store, "ws1", icp["id"], force=True)
    lead = store.create_lead("ws1", name="Acme", company_name="Acme Lettings Ltd", source="fixture")
    ab.rescore_after_enrichment(store, "ws1", lead["id"], reason="research_enrich")
    # second call: score unchanged
    result = ab.rescore_after_enrichment(store, "ws1", lead["id"], reason="companies_house_enrich")
    assert result["status"] == "unchanged"
    assert result["old"] == result["new"]


def test_rescore_recommends_suppression_below_threshold(store):
    from keprix.crm.icp import activate_icp, create_icp

    icp = create_icp(store, "ws1", name="Property", keywords=["letting"])
    activate_icp(store, "ws1", icp["id"], force=True)
    # lead with no ICP-matching keywords -> score 0
    lead = store.create_lead(
        "ws1", name="Random", company_name="Nothing Matches Ltd", source="fixture"
    )
    result = ab.rescore_after_enrichment(
        store, "ws1", lead["id"], reason="research_enrich", suppress_below=10
    )
    assert result["recommend_suppress"] is True
    assert result["new"] < 10


def test_attribute_reply_unmatched_without_outbound(store):
    # no outreach store rows -> unmatched, no crash
    class _EmptyOutreach:
        def get_lead(self, ws, lead_id):
            return {"id": lead_id, "email": "a@b.com"}

        def get_message(self, ws, mid):
            return None

        _conn = None

    outreach = _EmptyOutreach()
    # lead in crm store is required for workspace resolution; use a ws that exists
    store.create_lead("ws1", name="x", source="fixture")
    result = ab.attribute_reply(outreach, store, "ws1", "whatever")
    assert result["ok"] is True
    assert result["status"] == "unmatched"
