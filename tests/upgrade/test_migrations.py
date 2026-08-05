"""Tests for upgrade/migrations.py."""

from __future__ import annotations

from pathlib import Path

import yaml

from keprix.upgrade.migrations import (
    MIGRATIONS,
    MigrationStep,
    get_migration_plan,
    run_migration,
    run_rollback,
)


def _step(name: str, from_version: str) -> MigrationStep:
    def _noop(product_path: Path, backup_dir: Path) -> None:
        pass

    return MigrationStep(
        name=name,
        from_version=from_version,
        description=f"test migration {name}",
        reversible=True,
        execute=_noop,
        rollback=_noop,
    )


def test_get_migration_plan_empty_when_no_hop():
    plan = get_migration_plan("0.3.0", "0.3.0", registered=[])
    assert plan.count == 0


def test_get_migration_plan_selects_applicable_steps():
    registry = [
        _step("early", "0.4.0"),
        _step("mid", "0.5.0"),
        _step("late", "0.7.0"),
    ]
    plan = get_migration_plan("0.3.0", "0.7.0", registered=registry)
    names = [s.name for s in plan.steps]
    assert names == ["early", "mid", "late"]


def test_get_migration_plan_excludes_before_from_version():
    registry = [_step("old", "0.2.0"), _step("new", "0.5.0")]
    plan = get_migration_plan("0.3.0", "0.7.0", registered=registry)
    assert [s.name for s in plan.steps] == ["new"]


def test_builtin_migrations_include_config_layout():
    names = {m.name for m in MIGRATIONS}
    assert "config-layout-v2" in names
    assert "routing-config-v1" in names
    assert "audit-relocation" in names


def test_config_layout_v2_moves_providers_yaml(tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    old = config_dir / "providers.yaml"
    old.write_text("providers: []\n", encoding="utf-8")

    step = next(m for m in MIGRATIONS if m.name == "config-layout-v2")
    run_migration(step, tmp_path, tmp_path / "backup")

    assert not old.exists()
    assert (config_dir / "providers" / "providers.yaml").exists()


def test_config_layout_v2_rollback(tmp_path: Path):
    config_dir = tmp_path / "config"
    providers_dir = config_dir / "providers"
    providers_dir.mkdir(parents=True)
    new = providers_dir / "providers.yaml"
    new.write_text("providers: []\n", encoding="utf-8")

    step = next(m for m in MIGRATIONS if m.name == "config-layout-v2")
    run_rollback(step, tmp_path, tmp_path / "backup")

    assert (config_dir / "providers.yaml").exists()
    assert not new.exists()


def test_routing_section_added_to_manifest(tmp_path: Path):
    manifest = tmp_path / "keprix.yaml"
    manifest.write_text("product:\n  name: Test\nfeatures: {}\n", encoding="utf-8")

    step = next(m for m in MIGRATIONS if m.name == "routing-config-v1")
    run_migration(step, tmp_path, tmp_path / "backup")

    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert "routing" in data["features"]
    assert data["features"]["routing"]["enabled"] is False


def test_audit_relocation_moves_db(tmp_path: Path):
    old = tmp_path / "audit.db"
    old.write_bytes(b"sqlite")

    step = next(m for m in MIGRATIONS if m.name == "audit-relocation")
    run_migration(step, tmp_path, tmp_path / "backup")

    assert not old.exists()
    assert (tmp_path / "observability" / "audit.db").exists()
