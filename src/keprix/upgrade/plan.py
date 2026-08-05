"""Build step-by-step upgrade plans from changelog and migration data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .changelog import ChangelogRelease, entries_between
from .check import classify_risk
from .migrations import MigrationStep, get_migration_plan
from .versions import versions_between


@dataclass
class UpgradePlanStep:
    """One hop in an upgrade path (e.g. 0.3.0 -> 0.4.0)."""
    from_version: str
    to_version: str
    features: list[dict[str, Any]] = field(default_factory=list)
    config_migrations: list[dict[str, Any]] = field(default_factory=list)
    breaking_changes: list[dict[str, Any]] = field(default_factory=list)
    deprecations: list[dict[str, Any]] = field(default_factory=list)
    migration_steps: list[MigrationStep] = field(default_factory=list)
    risk: str = "none"


@dataclass
class UpgradePlan:
    """Full upgrade path from current to target Keprix version."""
    from_version: str
    to_version: str
    steps: list[UpgradePlanStep] = field(default_factory=list)
    direct_jump_recommended: bool = True

    @property
    def step_count(self) -> int:
        return len(self.steps)


def _entries_for_step(
    releases: list[ChangelogRelease],
    from_version: str,
    to_version: str,
) -> list[dict[str, Any]]:
    return entries_between(from_version, to_version, releases)


def build_upgrade_plan(
    from_version: str,
    to_version: str,
    available_versions: list[str],
    releases: list[ChangelogRelease] | None = None,
    registered_migrations: list[MigrationStep] | None = None,
) -> UpgradePlan:
    """Build a step-by-step upgrade plan across known release versions.

    Each step covers one version hop. Migrations that apply at a target version
    are attached to the step that reaches that version.
    """
    releases = releases or []
    hop_versions = versions_between(from_version, to_version, available_versions)
    if not hop_versions:
        return UpgradePlan(from_version=from_version, to_version=to_version, steps=[])

    steps: list[UpgradePlanStep] = []
    prev = from_version
    for target in hop_versions:
        step_entries = _entries_for_step(releases, prev, target)
        migration_plan = get_migration_plan(prev, target, registered=registered_migrations)
        steps.append(
            UpgradePlanStep(
                from_version=prev,
                to_version=target,
                features=[e for e in step_entries if e.get("type") == "feature"],
                config_migrations=[
                    e for e in step_entries if e.get("type") == "config_migration"
                ],
                breaking_changes=[e for e in step_entries if e.get("type") == "breaking"],
                deprecations=[e for e in step_entries if e.get("type") == "deprecation"],
                migration_steps=list(migration_plan.steps),
                risk=classify_risk(step_entries),
            )
        )
        prev = target

    return UpgradePlan(
        from_version=from_version,
        to_version=to_version,
        steps=steps,
        direct_jump_recommended=len(steps) > 1,
    )
