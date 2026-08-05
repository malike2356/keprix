"""Tests for upgrade/plan.py."""

from __future__ import annotations

from pathlib import Path

from keprix.upgrade.changelog import load_changelog
from keprix.upgrade.migrations import MIGRATIONS
from keprix.upgrade.plan import build_upgrade_plan

FIXTURES = Path(__file__).resolve().parent / "fixtures"
VERSIONS = ["0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0"]


def test_build_upgrade_plan_step_hops():
    releases = load_changelog(FIXTURES / "CHANGELOG.yaml")
    plan = build_upgrade_plan("0.3.0", "0.7.0", VERSIONS, releases=releases)
    assert plan.step_count == 4
    assert plan.steps[0].from_version == "0.3.0"
    assert plan.steps[0].to_version == "0.4.0"
    assert plan.steps[-1].to_version == "0.7.0"
    assert plan.direct_jump_recommended is True


def test_build_upgrade_plan_attaches_features_per_step():
    releases = load_changelog(FIXTURES / "CHANGELOG.yaml")
    plan = build_upgrade_plan("0.3.0", "0.5.0", VERSIONS, releases=releases)
    step_to_05 = plan.steps[-1]
    assert step_to_05.to_version == "0.5.0"
    assert len(step_to_05.features) == 1
    assert step_to_05.features[0]["id"] == "a2a"
    assert len(step_to_05.config_migrations) == 2


def test_build_upgrade_plan_includes_migrations_at_target():
    releases = load_changelog(FIXTURES / "CHANGELOG.yaml")
    plan = build_upgrade_plan(
        "0.3.0", "0.7.0", VERSIONS, releases=releases, registered_migrations=MIGRATIONS,
    )
    step_to_05 = next(s for s in plan.steps if s.to_version == "0.5.0")
    migration_names = {m.name for m in step_to_05.migration_steps}
    assert "config-layout-v2" in migration_names
    assert "audit-relocation" in migration_names


def test_build_upgrade_plan_risk_per_step():
    releases = load_changelog(FIXTURES / "CHANGELOG.yaml")
    plan = build_upgrade_plan("0.3.0", "0.7.0", VERSIONS, releases=releases)
    step_to_06 = next(s for s in plan.steps if s.to_version == "0.6.0")
    step_to_07 = next(s for s in plan.steps if s.to_version == "0.7.0")
    assert step_to_06.risk == "medium"
    assert step_to_07.risk == "high"


def test_build_upgrade_plan_empty_when_already_on_target():
    plan = build_upgrade_plan("0.7.0", "0.7.0", VERSIONS, releases=[])
    assert plan.step_count == 0
