"""Tests for BEACON copywriter module."""

from __future__ import annotations

import pytest

from keprix.personas.beacon.copywriter import BeaconCopywriter, BrandVoice


@pytest.fixture
def writer() -> BeaconCopywriter:
    return BeaconCopywriter(workspace_id="ws-beacon", user_id="user-beacon")


@pytest.fixture
def brand_voice() -> BrandVoice:
    return BrandVoice(
        client_name="Acme",
        voice_summary="Clear, helpful, professional.",
        banned_terms=["revolutionary", "game-changing"],
        reading_level_target=(8.0, 10.0),
    )


def test_normalize_typography_removes_smart_punctuation(writer: BeaconCopywriter) -> None:
    text = "Hello \u2014 world \u201cquote\u201d"
    normalized = writer.normalize_typography(text)
    assert "\u2014" not in normalized
    assert "\u201c" not in normalized


def test_validate_rejects_cliches(writer: BeaconCopywriter, brand_voice: BrandVoice) -> None:
    result = writer.validate_copy("This revolutionary platform is game-changing.", brand_voice)
    assert not result.passed
    assert any("Cliche" in issue for issue in result.issues)


def test_validate_rejects_banned_terms(writer: BeaconCopywriter, brand_voice: BrandVoice) -> None:
    result = writer.validate_copy("A revolutionary new way to work.", brand_voice)
    assert not result.passed


def test_readability_grade_computed(writer: BeaconCopywriter) -> None:
    text = "We help teams ship work faster. Our tools are simple and clear."
    grade = writer.readability_grade(text)
    assert grade >= 0


def test_save_and_load_brand_voice(writer: BeaconCopywriter, brand_voice: BrandVoice) -> None:
    writer.save_brand_voice("acme", brand_voice)
    loaded = writer.load_brand_voice("acme")
    assert loaded is not None
    assert loaded.client_name == "Acme"


def test_generate_copy_requires_brand_voice_on_first_interaction(writer: BeaconCopywriter) -> None:
    from keprix.personas.beacon.copywriter import BrandVoiceSetupRequired

    with pytest.raises(BrandVoiceSetupRequired) as exc:
        writer.generate_copy(format_type="email", brief={"body": "Hello"}, client_id="new-client")
    assert exc.value.prompt["required"] is True
    assert "brand voice" in exc.value.prompt["message"].lower()


def test_generate_copy_passes_validation(writer: BeaconCopywriter, brand_voice: BrandVoice) -> None:
    writer.save_brand_voice("acme", brand_voice)
    result = writer.generate_copy(
        format_type="email",
        brief={
            "subject": "Product update",
            "body": "We improved onboarding so your team can start faster.",
            "name": "Alex",
        },
        client_id="acme",
    )
    assert result.validation.passed
    assert result.document_id
    assert len(result.variants) == 3


def test_generate_copy_includes_word_count_for_long_form(writer: BeaconCopywriter, brand_voice: BrandVoice) -> None:
    writer.save_brand_voice("acme", brand_voice)
    long_body = " ".join(["Clear onboarding helps teams adopt tools faster."] * 60)
    result = writer.generate_copy(
        format_type="landing_page",
        brief={"headline": "Onboarding", "body": long_body},
        client_id="acme",
    )
    assert "Word count:" in result.content
