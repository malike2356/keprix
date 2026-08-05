"""Upgrade check: analyse whether a Keprix upgrade is safe.

Read-only. No files changed. Answers: "Should I upgrade and what is the risk?"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import UpgradeCheckResult
from .versions import version_gte, version_lt, version_tuple


def classify_risk(entries: list[dict[str, Any]]) -> str:
    """Classify upgrade risk from changelog entries."""
    breaking = [e for e in entries if e.get("type") == "breaking"]
    deprecated = [e for e in entries if e.get("type") == "deprecation"]
    migrations = [e for e in entries if e.get("type") == "config_migration"]
    if breaking:
        return "high"
    if deprecated:
        return "medium"
    if migrations:
        return "low"
    return "none"


@dataclass
class UpgradeManifestInfo:
    """Minimal product manifest info needed by check_upgrade()."""
    product_name: str
    keprix_tested_against: str     # version string the product was tested on
    keprix_min_version: str        # oldest Keprix version the product supports
    keprix_incompatible_with: list[str] = None  # known-bad Keprix versions

    def __post_init__(self):
        if self.keprix_incompatible_with is None:
            self.keprix_incompatible_with = []


def check_upgrade(
    manifest: UpgradeManifestInfo,
    current_keprix_version: str,
    target_version: str,
    available_versions: list[str],
    changelog: list[dict[str, Any]] | None = None,
    changelog_url: str = "",
) -> UpgradeCheckResult:
    """Analyse whether upgrading from current to target Keprix is safe.

    Args:
        manifest: Info about the product (min_version, incompatible_with, etc.)
        current_keprix_version: The installed Keprix version string.
        target_version: The version to upgrade to.
        available_versions: All known versions (from release registry or PyPI).
        changelog: List of changelog entry dicts from CHANGELOG.yaml.
        changelog_url: URL to the release notes for target_version.

    Returns:
        UpgradeCheckResult with risk level and recommendation.
    """
    changelog = changelog or []

    # Already on target
    if version_gte(current_keprix_version, target_version):
        return UpgradeCheckResult(
            product=manifest.product_name,
            current_version=current_keprix_version,
            target_version=target_version,
            available_versions=available_versions,
            compatible=True,
            risk="none",
            breaking_changes=[],
            deprecated_features=[],
            new_features=[],
            config_migrations_required=[],
            recommendation=f"Already on {current_keprix_version}. No upgrade needed.",
            changelog_url=changelog_url,
        )

    # Target is below minimum supported
    if version_lt(target_version, manifest.keprix_min_version):
        return UpgradeCheckResult(
            product=manifest.product_name,
            current_version=current_keprix_version,
            target_version=target_version,
            available_versions=available_versions,
            compatible=False,
            risk="blocked",
            breaking_changes=[],
            deprecated_features=[],
            new_features=[],
            config_migrations_required=[],
            recommendation=(
                f"Cannot upgrade to {target_version}. "
                f"{manifest.product_name} requires Keprix >= {manifest.keprix_min_version}."
            ),
            changelog_url=changelog_url,
        )

    # Target is known-incompatible
    for bad in manifest.keprix_incompatible_with:
        if version_tuple(bad) == version_tuple(target_version):
            return UpgradeCheckResult(
                product=manifest.product_name,
                current_version=current_keprix_version,
                target_version=target_version,
                available_versions=available_versions,
                compatible=False,
                risk="blocked",
                breaking_changes=[],
                deprecated_features=[],
                new_features=[],
                config_migrations_required=[],
                recommendation=(
                    f"{target_version} is marked incompatible by "
                    f"{manifest.product_name}. Wait for a fix."
                ),
                changelog_url=changelog_url,
            )

    # Classify changelog entries
    breaking = [e for e in changelog if e.get("type") == "breaking"]
    deprecated = [e for e in changelog if e.get("type") == "deprecation"]
    new_features = [e for e in changelog if e.get("type") == "feature"]
    migrations = [e for e in changelog if e.get("type") == "config_migration"]
    risk = classify_risk(changelog)

    if risk == "high":
        rec = (
            f"{len(breaking)} breaking change(s) between {current_keprix_version} "
            f"and {target_version}. Review carefully before upgrading."
        )
    elif risk == "medium":
        rec = (
            f"{len(deprecated)} deprecation(s). Plan migration within 2 releases."
        )
    elif risk == "low":
        rec = f"{len(migrations)} optional config migration(s). Safe to upgrade."
    else:
        rec = (
            f"Safe to upgrade to {target_version}. "
            f"{len(new_features)} new feature(s) available."
        )

    return UpgradeCheckResult(
        product=manifest.product_name,
        current_version=current_keprix_version,
        target_version=target_version,
        available_versions=available_versions,
        compatible=True,
        risk=risk,
        breaking_changes=breaking,
        deprecated_features=deprecated,
        new_features=new_features,
        config_migrations_required=migrations,
        recommendation=rec,
        changelog_url=changelog_url,
    )
