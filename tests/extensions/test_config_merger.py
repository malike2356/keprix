"""Tests for extensions/config_merger.py."""

from __future__ import annotations

import pytest

from keprix.extensions.config_merger import ConfigMerger, deep_merge


def test_deep_merge_scalars():
    base = {"a": 1, "b": 2}
    override = {"b": 99, "c": 3}
    result = deep_merge(base, override)
    assert result == {"a": 1, "b": 99, "c": 3}


def test_deep_merge_nested_dicts():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"port": 9999}}
    result = deep_merge(base, override)
    assert result["db"]["host"] == "localhost"
    assert result["db"]["port"] == 9999


def test_deep_merge_list_replaced():
    base = {"items": [1, 2, 3]}
    override = {"items": [4, 5]}
    result = deep_merge(base, override)
    assert result["items"] == [4, 5]


def test_deep_merge_does_not_mutate_base():
    base = {"a": {"x": 1}}
    override = {"a": {"y": 2}}
    deep_merge(base, override)
    assert "y" not in base["a"]


def test_config_merger_apply():
    merger = ConfigMerger(base_config={"logging": "info", "billing": {"enabled": True}})
    result = merger.apply({"billing": {"plan": "pro"}, "feature_flag": True})
    assert result["logging"] == "info"
    assert result["billing"]["plan"] == "pro"
    assert result["billing"]["enabled"] is True


def test_config_merger_apply_all():
    merger = ConfigMerger(base_config={"base": True})
    result = merger.apply_all([
        {"product": "abbis"},
        {"region": "eu"},
    ])
    assert result["base"] is True
    assert result["product"] == "abbis"
    assert result["region"] == "eu"


def test_config_merger_validate_no_conflicts_clean():
    merger = ConfigMerger()
    conflicts = merger.validate_no_conflicts([
        {"abbis": {"wells": 10}},
        {"petraclus": {"scans": 5}},
    ])
    assert conflicts == []


def test_config_merger_validate_detects_conflict():
    merger = ConfigMerger()
    conflicts = merger.validate_no_conflicts([
        {"billing": {"plan": "a"}},
        {"billing": {"plan": "b"}},
    ])
    assert "billing" in conflicts


def test_config_merger_strict_keys_blocks_override():
    merger = ConfigMerger()
    conflicts = merger.validate_no_conflicts(
        [{"security": {"tls": True}}],
        strict_keys=["security"],
    )
    assert any("security" in c for c in conflicts)
