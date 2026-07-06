"""Tests for config-driven product registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.products.loader import (
    get_default_audit_domain_pack,
    get_regulated_domains,
    list_enabled_products,
    load_products_config,
    reset_products_cache,
)


@pytest.fixture
def products_env(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("KEPRIX_PRODUCTS_CONFIG", str(repo_root / "config" / "products.example.yaml"))
    reset_products_cache()
    yield
    reset_products_cache()


def test_no_products_enabled_by_default(products_env, monkeypatch) -> None:
    monkeypatch.delenv("KEPRIX_ENABLED_PRODUCTS", raising=False)
    reset_products_cache()
    assert list_enabled_products() == []
    assert get_default_audit_domain_pack() is None


def test_abbis_borehole_loads_intent_config(products_env, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_ENABLED_PRODUCTS", "abbis_borehole")
    reset_products_cache()
    from keprix.backend.intent.registry import reset_intent_registry
    from keprix.backend.intent.domain_intents import load_product_domain_intents

    intents = load_product_domain_intents()
    assert any(row.name == "request_drilling_quote" for row in intents)


def test_compass_compliance_sets_audit_domain_pack(products_env, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_ENABLED_PRODUCTS", "compass_compliance")
    monkeypatch.setenv("COMPASS_ENABLED", "true")
    reset_products_cache()
    load_products_config(force=True)
    assert get_default_audit_domain_pack() == "compass-compliance"


def test_regulated_domains_include_defaults_and_product_domains(products_env, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_ENABLED_PRODUCTS", "abbis_borehole")
    reset_products_cache()
    domains = get_regulated_domains()
    assert "healthcare" in domains
    assert "borehole_drilling" in domains
