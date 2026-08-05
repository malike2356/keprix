"""Tests for resilience/graceful_degrade.py."""

from __future__ import annotations

import pytest

from keprix.providers.resilience.graceful_degrade import DegradeLevel, GracefulDegrader


@pytest.fixture
def degrader():
    return GracefulDegrader(all_tier_ids=["premium", "subscription", "free", "fallback"])


def test_initial_status_is_full(degrader):
    status = degrader.current_status()
    assert status.level == DegradeLevel.FULL
    assert len(status.available_tiers) == 4
    assert status.failed_tiers == []


def test_one_tier_failed_gives_partial(degrader):
    degrader.mark_tier_failed("premium")
    status = degrader.current_status()
    assert status.level == DegradeLevel.PARTIAL
    assert "premium" in status.failed_tiers
    assert "premium" not in status.available_tiers


def test_all_but_one_tier_failed_gives_minimal(degrader):
    degrader.mark_tier_failed("premium")
    degrader.mark_tier_failed("subscription")
    degrader.mark_tier_failed("free")
    status = degrader.current_status()
    assert status.level == DegradeLevel.MINIMAL
    assert status.available_tiers == ["fallback"]


def test_all_tiers_failed_gives_offline(degrader):
    for t in ["premium", "subscription", "free", "fallback"]:
        degrader.mark_tier_failed(t)
    status = degrader.current_status()
    assert status.level == DegradeLevel.OFFLINE
    assert status.available_tiers == []


def test_recovery_restores_tier(degrader):
    degrader.mark_tier_failed("premium")
    degrader.mark_tier_recovered("premium")
    status = degrader.current_status()
    assert status.level == DegradeLevel.FULL


def test_should_stub_when_offline(degrader):
    for t in ["premium", "subscription", "free", "fallback"]:
        degrader.mark_tier_failed(t)
    assert degrader.should_stub()


def test_should_not_stub_when_partial(degrader):
    degrader.mark_tier_failed("premium")
    assert not degrader.should_stub()


def test_build_stub_message_is_valid_response(degrader):
    stub = degrader.build_stub_message()
    assert stub["choices"][0]["message"]["role"] == "assistant"
    assert stub["_keprix_stub"] is True


def test_build_stub_message_includes_extra(degrader):
    stub = degrader.build_stub_message(extra="retry in 60s")
    content = stub["choices"][0]["message"]["content"]
    assert "retry in 60s" in content


def test_idempotent_fail_mark(degrader):
    degrader.mark_tier_failed("premium")
    degrader.mark_tier_failed("premium")
    assert degrader.current_status().failed_tiers.count("premium") == 1
