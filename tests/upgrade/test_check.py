"""Tests for upgrade/check.py."""

from __future__ import annotations

import pytest

from keprix.upgrade.check import UpgradeManifestInfo, check_upgrade


def _manifest(
    product_name="TestProduct",
    tested_against="0.3.0",
    min_version="0.2.0",
    incompatible_with=None,
):
    return UpgradeManifestInfo(
        product_name=product_name,
        keprix_tested_against=tested_against,
        keprix_min_version=min_version,
        keprix_incompatible_with=incompatible_with or [],
    )


def _changelog(*entry_types: str) -> list[dict]:
    """Build a minimal changelog with entries of the given types."""
    return [{"type": t, "title": f"Entry {i}"} for i, t in enumerate(entry_types)]


VERSIONS = ["0.1.0", "0.2.0", "0.3.0", "0.5.0", "0.7.0"]


def test_already_on_target():
    manifest = _manifest(tested_against="0.7.0")
    result = check_upgrade(manifest, "0.7.0", "0.7.0", VERSIONS)
    assert result.risk == "none"
    assert "No upgrade needed" in result.recommendation
    assert result.compatible


def test_already_ahead_of_target():
    manifest = _manifest()
    result = check_upgrade(manifest, "0.7.0", "0.5.0", VERSIONS)
    assert result.risk == "none"
    assert result.compatible


def test_safe_upgrade_no_changes():
    manifest = _manifest(tested_against="0.3.0", min_version="0.2.0")
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=[])
    assert result.risk == "none"
    assert result.compatible
    assert "Safe to upgrade" in result.recommendation


def test_low_risk_with_migrations():
    changelog = _changelog("config_migration", "config_migration")
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=changelog)
    assert result.risk == "low"
    assert len(result.config_migrations_required) == 2
    assert result.compatible


def test_medium_risk_with_deprecations():
    changelog = _changelog("deprecation")
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=changelog)
    assert result.risk == "medium"
    assert len(result.deprecated_features) == 1
    assert result.compatible


def test_high_risk_with_breaking_changes():
    changelog = _changelog("breaking", "breaking", "feature")
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=changelog)
    assert result.risk == "high"
    assert len(result.breaking_changes) == 2
    assert result.compatible


def test_blocked_below_min_version():
    manifest = _manifest(min_version="0.6.0")
    result = check_upgrade(manifest, "0.3.0", "0.5.0", VERSIONS)
    assert result.risk == "blocked"
    assert not result.compatible
    assert "requires Keprix" in result.recommendation


def test_blocked_incompatible_version():
    manifest = _manifest(incompatible_with=["0.5.0"])
    result = check_upgrade(manifest, "0.3.0", "0.5.0", VERSIONS)
    assert result.risk == "blocked"
    assert not result.compatible
    assert "incompatible" in result.recommendation


def test_new_features_counted():
    changelog = _changelog("feature", "feature", "feature")
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=changelog)
    assert len(result.new_features) == 3
    assert "3 new feature" in result.recommendation


def test_to_dict_includes_risk():
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=[])
    d = result.to_dict()
    assert "risk" in d
    assert d["product"] == "TestProduct"
    assert d["current_version"] == "0.3.0"
    assert d["target_version"] == "0.7.0"


def test_changelog_url_propagated():
    manifest = _manifest()
    result = check_upgrade(
        manifest, "0.3.0", "0.7.0", VERSIONS,
        changelog_url="https://example.com/releases/0.7.0"
    )
    assert result.changelog_url == "https://example.com/releases/0.7.0"


def test_breaking_overrides_deprecated():
    changelog = _changelog("breaking", "deprecation")
    manifest = _manifest()
    result = check_upgrade(manifest, "0.3.0", "0.7.0", VERSIONS, changelog=changelog)
    assert result.risk == "high"
