"""Tests for billing.yaml loading and validation."""

from __future__ import annotations

import pytest

from keprix.billing.config_loader import billing_enabled, load_billing_config, resolve_billing_config_path
from keprix.billing.schema import BillingConfig


def test_load_example_config():
    cfg = load_billing_config(force_reload=True)
    assert cfg is not None
    assert cfg.product.id == "example-saas"
    assert len(cfg.plans) == 3
    assert cfg.plan_by_id("pro") is not None


def test_billing_enabled_in_mock_mode():
    assert billing_enabled() is True


def test_community_plan_detection():
    cfg = load_billing_config(force_reload=True)
    assert cfg is not None
    community = cfg.community_plan()
    assert community is not None
    assert community.id == "community"


def test_invalid_config_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("product:\n  id: x\nplans: []\n", encoding="utf-8")
    with pytest.raises(Exception):
        BillingConfig.model_validate({"product": {"id": "x", "name": "X", "company": "C"}, "plans": []})


def test_resolve_config_path():
    path = resolve_billing_config_path()
    assert path is not None
    assert path.name == "billing.example.yaml"
