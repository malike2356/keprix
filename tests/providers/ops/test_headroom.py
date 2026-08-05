"""Tests for ops/headroom.py."""

from __future__ import annotations

import pytest

from keprix.providers.ops.headroom import HeadroomDetector


@pytest.fixture
def detector():
    return HeadroomDetector(avg_tokens_per_call=1000, warn_calls_threshold=100, critical_calls_threshold=10)


def test_unknown_tokens_gives_ok_risk(detector):
    result = detector.compute("openai", tokens_remaining=-1)
    assert result.tokens_remaining == -1
    assert result.risk_level == "ok"


def test_zero_tokens_gives_critical(detector):
    result = detector.compute("openai", tokens_remaining=0)
    assert result.risk_level == "critical"


def test_low_calls_remaining_critical(detector):
    result = detector.compute("openai", tokens_remaining=5_000)
    assert result.estimated_calls_remaining == 5
    assert result.risk_level == "critical"


def test_medium_calls_remaining_warn(detector):
    result = detector.compute("openai", tokens_remaining=50_000)
    assert result.estimated_calls_remaining == 50
    assert result.risk_level == "warn"


def test_plenty_of_tokens_ok(detector):
    result = detector.compute("openai", tokens_remaining=500_000)
    assert result.risk_level == "ok"


def test_budget_exhausted_gives_critical(detector):
    result = detector.compute("openai", tokens_remaining=100_000, spend_usd=50.0, budget_usd=50.0)
    assert result.risk_level == "critical"
    assert result.budget_remaining_usd == 0.0


def test_budget_low_gives_warn(detector):
    result = detector.compute("openai", tokens_remaining=500_000, spend_usd=46.0, budget_usd=50.0)
    assert result.risk_level == "warn"


def test_exhaustion_eta_computed_with_burn_rate(detector):
    result = detector.compute("openai", tokens_remaining=10_000, burn_rate_tokens_per_sec=100.0)
    assert result.exhaustion_eta is not None


def test_no_burn_rate_no_eta(detector):
    result = detector.compute("openai", tokens_remaining=10_000, burn_rate_tokens_per_sec=0.0)
    assert result.exhaustion_eta is None


def test_no_budget_returns_minus_one(detector):
    result = detector.compute("openai", tokens_remaining=100_000, budget_usd=-1.0)
    assert result.budget_remaining_usd == -1.0
