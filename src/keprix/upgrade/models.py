"""Shared data models for the Keprix upgrade system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UpgradeCheckResult:
    """Result of `keprix upgrade --check`."""
    product: str
    current_version: str
    target_version: str
    available_versions: list[str]
    compatible: bool
    risk: str                         # "none" | "low" | "medium" | "high" | "blocked"
    breaking_changes: list[dict]
    deprecated_features: list[dict]
    new_features: list[dict]
    config_migrations_required: list[dict]
    recommendation: str
    changelog_url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "current_version": self.current_version,
            "target_version": self.target_version,
            "compatible": self.compatible,
            "risk": self.risk,
            "breaking_changes_count": len(self.breaking_changes),
            "deprecated_count": len(self.deprecated_features),
            "new_features_count": len(self.new_features),
            "migrations_count": len(self.config_migrations_required),
            "recommendation": self.recommendation,
            "changelog_url": self.changelog_url,
        }


@dataclass
class DryRunResult:
    product: str
    target_version: str
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    warnings: list[str]
    failed_test_details: list[str]
    duration_seconds: float
    recommendation: str


@dataclass
class UpgradeRecord:
    """A single entry in the upgrade history log."""
    from_version: str
    to_version: str
    timestamp: str
    backup_path: str
    status: str    # "success" | "failed" | "rolled_back"
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_version,
            "to": self.to_version,
            "timestamp": self.timestamp,
            "backup_path": self.backup_path,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
        }
