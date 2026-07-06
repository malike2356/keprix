"""Tests for WARDEN hardener module."""

from __future__ import annotations

import pytest

from keprix.personas.warden.hardener import WardenHardener


@pytest.fixture
def hardener() -> WardenHardener:
    return WardenHardener()


def test_assess_recommends_disable_debug(hardener: WardenHardener) -> None:
    recommendations = hardener.assess({"debug": True})
    ids = {rec.id for rec in recommendations}
    assert "debug_disabled" in ids


def test_assess_recommends_docker_hardening(hardener: WardenHardener) -> None:
    recommendations = hardener.assess({"docker_privileged": True, "docker_drop_caps": False})
    ids = {rec.id for rec in recommendations}
    assert "docker_no_privileged" in ids
    assert "docker_drop_caps" in ids


def test_apply_requires_approval(hardener: WardenHardener) -> None:
    config = {"debug": True}
    result = hardener.apply("debug_disabled", config, approved=False)
    assert not result["applied"]
    assert result["reason"] == "approval required"


def test_apply_patches_config_when_approved(hardener: WardenHardener) -> None:
    config = {"debug": True, "rate_limit_enabled": False}
    result = hardener.apply("debug_disabled", config, approved=True)
    assert result["applied"]
    assert config["debug"] is False
