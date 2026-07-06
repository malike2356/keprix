"""Tests for Asset Factory playbook."""

from __future__ import annotations

import pytest

from keprix.opportunity.models import OpportunityRequest
from keprix.opportunity.orchestrator import run_opportunity_phase
from keprix.opportunity.playbooks.asset_factory import (
    DEFAULT_ASSET_FILES,
    MissingOfferDocError,
    UnsupportedClaimError,
    _enforce_claim_rules,
    build_all_assets,
    resolve_offer_context,
    run_asset_factory_playbook,
    validate_asset_claims,
)
from keprix.opportunity.playbooks.offer_builder import OfferBuilderInput, run_offer_builder_playbook
from keprix.opportunity.playbooks.offer_doc_generator import run_offer_doc_generator_playbook
from keprix.opportunity.playbooks.validation_score import run_validation_score_playbook
from keprix.opportunity.registry import reset_opportunity_registry
from keprix.opportunity.workspace import (
    create_opportunity_workspace,
    read_artifact,
    read_opportunity_asset,
    read_opportunity_json,
    update_opportunity_json,
)
from keprix.security.rate_limiter import reset_rate_limits


@pytest.fixture
def opp_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(data_dir))
    reset_rate_limits()
    reset_opportunity_registry(base_dir=data_dir / "workspace" / "opportunities")
    return data_dir


async def _prepare_offer_doc(opp_id: str, workspace_id: str = "default") -> None:
    await run_offer_builder_playbook(
        workspace_id=workspace_id,
        opportunity_id=opp_id,
        request=OfferBuilderInput(niche="legal tech", title="Asset Test", goal="validate"),
    )
    await run_validation_score_playbook(workspace_id=workspace_id, opportunity_id=opp_id)
    await run_offer_doc_generator_playbook(workspace_id=workspace_id, opportunity_id=opp_id)
    update_opportunity_json(opp_id, {"validation_override": True})


@pytest.mark.asyncio
async def test_asset_factory_creates_all_files(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Asset Factory", niche="legal tech", source="test"),
    )
    await _prepare_offer_doc(workspace.opportunity_id, workspace.workspace_id)

    result = await run_opportunity_phase(workspace.opportunity_id, "asset_factory")
    for name in ("07-funnel.md", "08-content-assets.md", "09-ads.md", "10-sales-deck.md"):
        assert name in result["artifacts_written"]
    for name in DEFAULT_ASSET_FILES:
        assert f"assets/{name}" in result["artifacts_written"]

    funnel = read_artifact(workspace.opportunity_id, "07-funnel.md")
    assert "DRAFT" in funnel

    landing = read_opportunity_asset(workspace.opportunity_id, "landing-page.md")
    assert "Hero" in landing
    assert "PROOF PLACEHOLDER" in landing

    ads = read_artifact(workspace.opportunity_id, "09-ads.md")
    assert len([line for line in ads.splitlines() if line.strip().startswith("- ")]) >= 10

    nurture = read_opportunity_asset(workspace.opportunity_id, "email-nurture-sequence.md")
    assert nurture.count("## Email") >= 5

    meta = read_opportunity_json(workspace.opportunity_id)
    assert meta.get("asset_factory_status") == "draft"


@pytest.mark.asyncio
async def test_missing_offer_doc_raises(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="No Offer Doc", niche="saas", source="test"),
    )
    with pytest.raises(MissingOfferDocError):
        await run_asset_factory_playbook(
            workspace_id=workspace.workspace_id,
            opportunity_id=workspace.opportunity_id,
        )


@pytest.mark.asyncio
async def test_unsupported_claim_detection(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="Claim Test", niche="fintech", source="test"),
    )
    await _prepare_offer_doc(workspace.opportunity_id, workspace.workspace_id)
    doc, _, _, meta = resolve_offer_context(workspace.opportunity_id)

    violations = validate_asset_claims(
        "Guaranteed income for every customer in 30 days",
        meta=meta,
        doc=doc,
    )
    assert violations

    bad_files = build_all_assets(doc=doc, meta=meta)
    bad_files["09-ads.md"] += "\nGuaranteed income for all buyers"
    with pytest.raises(UnsupportedClaimError):
        _enforce_claim_rules(bad_files, meta=meta, doc=doc)


@pytest.mark.asyncio
async def test_uses_canonical_offer_icp_language(opp_env):
    workspace = create_opportunity_workspace(
        OpportunityRequest(title="ICP Language", niche="proptech", source="test"),
    )
    await _prepare_offer_doc(workspace.opportunity_id, workspace.workspace_id)
    doc, offer_md, _, _ = resolve_offer_context(workspace.opportunity_id)

    files = await run_asset_factory_playbook(
        workspace_id=workspace.workspace_id,
        opportunity_id=workspace.opportunity_id,
    )

    assert doc.primary_icp
    assert doc.primary_icp in files["assets/landing-page.md"]
    assert doc.offer_name in offer_md or "Canonical Offer Doc" in offer_md
