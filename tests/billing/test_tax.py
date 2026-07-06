"""Tests for tax calculation."""

from __future__ import annotations

from keprix.billing.tax.calculator import calculate_tax


def test_uk_vat():
    result = calculate_tax("GB", None, 10000)
    assert result.amount == 2000
    assert result.rate == 0.20


def test_us_no_tax():
    result = calculate_tax("US", None, 10000)
    assert result.amount == 0


def test_eu_b2b_reverse_charge():
    result = calculate_tax("DE", "DE123456789", 10000)
    assert result.amount == 0
    assert "reverse charge" in result.label.lower()


def test_eu_consumer_moss():
    result = calculate_tax("DE", None, 10000)
    assert result.amount > 0
