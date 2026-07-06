"""Tests for BEACON delivery module."""

from __future__ import annotations

import pytest

from keprix.personas.beacon.copywriter import BeaconCopywriter, BrandVoice
from keprix.personas.beacon.delivery import BeaconDelivery


@pytest.fixture
def delivery() -> BeaconDelivery:
    return BeaconDelivery(workspace_id="ws-beacon", user_id="user-beacon")


@pytest.fixture
def configured_voice() -> None:
    writer = BeaconCopywriter(workspace_id="ws-beacon", user_id="user-beacon")
    writer.save_brand_voice(
        "acme",
        BrandVoice(
            client_name="Acme",
            voice_summary="Professional and clear.",
            banned_terms=["revolutionary"],
        ),
    )


def test_review_fails_on_cliche(delivery: BeaconDelivery, configured_voice: None) -> None:
    review = delivery.review_deliverable("Our revolutionary platform changes everything.", client_id="acme")
    assert not review.passed


@pytest.mark.asyncio
async def test_prepare_pdf_deliverable(delivery: BeaconDelivery, configured_voice: None) -> None:
    package = await delivery.prepare_deliverable(
        title="Client Proposal",
        content=(
            "We help your team launch campaigns with clear messaging. "
            "Our work covers planning, writing, and client-ready files. "
            "Each file is checked for brand voice and quality before delivery."
        ),
        output_format="pdf",
        client_id="acme",
    )
    assert package.review.passed
    assert package.mime_type == "application/pdf"
    assert isinstance(package.content, bytes)
    assert package.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_prepare_slides_deliverable(delivery: BeaconDelivery, configured_voice: None) -> None:
    package = await delivery.prepare_deliverable(
        title="Pitch Deck",
        content="## Problem\nTeams need clearer messaging.\n\n## Solution\nBEACON delivers on-brand copy.",
        output_format="slides",
        client_id="acme",
    )
    assert "---" in package.content
    assert "Slide" in package.content


@pytest.mark.asyncio
async def test_localize_passthrough_english(delivery: BeaconDelivery) -> None:
    result = await delivery.localize_content("Hello world", "en-US")
    assert result.translated_text == "Hello world"
    assert result.provider == "passthrough"
