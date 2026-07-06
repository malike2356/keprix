"""Tests for canonical Offer Doc generator and agent memory."""

from __future__ import annotations

import pytest

from keprix.memory.episodic.store import InMemoryEpisodicStore
from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.offer_doc_generator import (
    build_canonical_offer_from_meta,
    load_canonical_offer_doc,
    render_agent_memory_brief,
    run_offer_doc_generator_playbook,
    store_opportunity_scoped_memory,
)
from keprix.opportunity.playbooks.validation_score import run_validation_score_playbook
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.workspace import create_opportunity_workspace, read_artifact, read_opportunity_json
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return data_dir


def test_missing_validation_score_handled():
    doc = build_canonical_offer_from_meta({"title": "Test", "niche": "saas"})
    assert doc.validation_score is None
    assert "validation" in doc.validation_recommendation.lower() or "not" in doc.validation_recommendation.lower()
    assert doc.open_questions


def test_forbidden_claims_present():
    doc = build_canonical_offer_from_meta({"title": "Test", "niche": "saas"})
    assert any("guaranteed" in c.lower() for c in doc.claims_forbidden)


def test_memory_brief_is_concise():
    doc = build_canonical_offer_from_meta(
        {
            "title": "Brief Test",
            "niche": "saas",
            "offer": {"core_promise": "Save time", "unique_mechanism": "Playbooks"},
            "icp": {"primary": {"summary": "SMB founders"}},
        },
    )
    brief = render_agent_memory_brief(opportunity_name="Brief Test", doc=doc)
    assert len(brief) <= 2600
    assert "Never make these claims" in brief


@pytest.mark.asyncio
async def test_scoped_memory_tags(opp_env, monkeypatch):
    store = InMemoryEpisodicStore()
    monkeypatch.setattr(
        "keprix.opportunity.playbooks.offer_doc_generator.memory_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "keprix.memory.episodic.store.create_episodic_store",
        lambda *a, **k: store,
    )

    memory_id = await store_opportunity_scoped_memory(
        workspace_id="ws-1",
        opportunity_id="opp-test1234",
        brief="test brief",
        user_id="user-a",
    )
    assert memory_id
    rows = await store.list_all("user-a")
    assert rows[0].metadata.get("opportunity_id") == "opp-test1234"
    assert "offer" in (rows[0].metadata.get("tags") or [])


@pytest.mark.asyncio
async def test_generator_writes_canonical_doc_and_brief(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Canonical", niche="legal tech", source="test"),
    )
    await run_offer_builder_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
        request=OfferBuilderInput(niche="legal tech", title="Canonical", goal="test"),
    )
    await run_validation_score_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    await run_offer_doc_generator_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )
    canonical = read_artifact(workspace.opportunity_id, "05-offer-doc.md")
    brief = read_artifact(workspace.opportunity_id, "agent-memory-brief.md")
    meta = read_opportunity_json(workspace.opportunity_id)
    assert "# Canonical Offer Doc" in canonical
    assert "## Claims Agents Must Not Make" in canonical
    assert "# Agent Memory Brief" in brief
    assert meta["claims_forbidden"]
    assert load_canonical_offer_doc(workspace.opportunity_id)


@pytest.mark.asyncio
async def test_orchestrator_offer_doc_phase(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Orch Doc", niche="edtech", source="test"),
    )
    await run_opportunity_phase(workspace.opportunity_id, "offer_builder")
    await run_opportunity_phase(workspace.opportunity_id, "offer_doc")
    canonical = read_artifact(workspace.opportunity_id, "05-offer-doc.md")
    assert "Canonical Offer Doc" in canonical
