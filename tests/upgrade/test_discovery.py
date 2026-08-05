"""Tests for upgrade/discovery.py."""

from __future__ import annotations

from keprix.upgrade.discovery import FeatureDiscovery, FeatureInfo


def test_get_new_features_between_versions():
    discovery = FeatureDiscovery()
    features = discovery.get_new_features("0.3.0", "0.5.0")
    names = {f.name for f in features}
    assert "billing" in names
    assert "combo_routing" in names
    assert "compression" in names
    assert "notion" not in names


def test_get_breaking_changes():
    discovery = FeatureDiscovery()
    breaking = discovery.get_breaking_changes("0.3.0", "0.5.0")
    assert len(breaking) == 1
    assert breaking[0].name == "governance"


def test_get_opt_in_features():
    discovery = FeatureDiscovery()
    opt_in = discovery.get_opt_in_features("0.3.0", "0.6.0")
    names = {f.name for f in opt_in}
    assert "billing" in names
    assert "notion" in names
    assert "compression" not in names


def test_custom_registry():
    registry = {
        "1.0.0": [
            FeatureInfo(
                name="demo",
                description="demo feature",
                module="demo",
                version="1.0.0",
            )
        ]
    }
    discovery = FeatureDiscovery(registry=registry)
    assert discovery.get_new_features("0.9.0", "1.0.0")[0].name == "demo"
