"""Tests for BEACON campaign module."""

from __future__ import annotations

import pytest

from keprix.personas.beacon.campaign import BeaconCampaign


@pytest.fixture
def campaign() -> BeaconCampaign:
    return BeaconCampaign(workspace_id="ws-beacon")


def test_plan_campaign_includes_multiple_channels(campaign: BeaconCampaign) -> None:
    plan = campaign.plan_campaign(
        campaign_name="Launch Q3",
        objective="Drive qualified demo requests",
        client_name="Acme",
        channels=["email", "social", "landing"],
        duration_days=14,
    )
    assert len(plan.channels) == 3
    assert len(plan.assets) >= 3


def test_asset_calendar_has_due_dates(campaign: BeaconCampaign) -> None:
    plan = campaign.plan_campaign(
        campaign_name="Launch",
        objective="Awareness",
        client_name="Acme",
        channels=["email", "ads"],
        duration_days=10,
    )
    assert all(asset.due_date for asset in plan.assets)


def test_brief_markdown_includes_calendar(campaign: BeaconCampaign) -> None:
    plan = campaign.plan_campaign(
        campaign_name="Launch",
        objective="Leads",
        client_name="Acme",
        channels=["email", "blog"],
    )
    assert "Asset Calendar" in plan.brief_markdown
    assert "email" in plan.brief_markdown


def test_opportunity_asset_mapping(campaign: BeaconCampaign) -> None:
    assets = campaign.opportunity_assets_for_channels(["email", "ads"])
    assert "email-nurture-sequence.md" in assets
    assert "ad-copy.md" in assets
