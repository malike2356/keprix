"""Migration framework for Keprix version upgrades.

Each migration is a named, versioned step that transforms product config
or data from one Keprix schema to another. Migrations run in version order
during `keprix upgrade --to <version>`.

Migrations are reversible (rollback) when possible. If a migration provides
no rollback, rolling back past it will log a warning but will not block.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .versions import version_gt, version_lte, version_tuple

logger = logging.getLogger(__name__)

MigrateFn = Callable[[Path, Path], None]


@dataclass
class MigrationStep:
    """A single config/data migration step."""
    name: str
    from_version: str           # e.g. "0.5.0"; migration runs when upgrading past this
    description: str
    reversible: bool
    execute: MigrateFn
    rollback: Optional[MigrateFn] = None


@dataclass
class MigrationPlan:
    """Ordered list of migration steps to apply during an upgrade."""
    steps: list[MigrationStep] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.steps)


# Registry of all known migrations (populated by register_migration calls below)
MIGRATIONS: list[MigrationStep] = []


def register_migration(step: MigrationStep) -> None:
    """Register a migration step. Called at module initialisation."""
    MIGRATIONS.append(step)


def get_migration_plan(
    from_version: str,
    to_version: str,
    registered: list[MigrationStep] | None = None,
) -> MigrationPlan:
    """Return the ordered migrations needed to go from from_version to to_version.

    A migration with from_version "0.5.0" is included if:
      from_version < "0.5.0" <= to_version
    """
    registry = registered if registered is not None else MIGRATIONS

    applicable = [
        m for m in registry
        if version_gt(m.from_version, from_version) and version_lte(m.from_version, to_version)
    ]
    # Sort by from_version ascending so migrations run in order
    applicable.sort(key=lambda m: version_tuple(m.from_version))
    return MigrationPlan(steps=applicable)


def run_migration(step: MigrationStep, product_path: Path, backup_dir: Path) -> None:
    """Execute a single migration step."""
    step.execute(product_path, backup_dir)


def run_rollback(step: MigrationStep, product_path: Path, backup_dir: Path) -> bool:
    """Execute a migration step's rollback. Returns True if successful."""
    if step.rollback is None:
        logger.warning("Migration '%s' has no rollback; skipping.", step.name)
        return True
    step.rollback(product_path, backup_dir)
    return True


# ---------------------------------------------------------------------------
# Built-in migrations
# ---------------------------------------------------------------------------

def _migrate_config_layout_v2(product_path: Path, backup_dir: Path) -> None:
    """Move providers.yaml to providers/ subdirectory."""
    old = product_path / "config" / "providers.yaml"
    new_dir = product_path / "config" / "providers"
    if old.exists() and not new_dir.exists():
        new_dir.mkdir(parents=True)
        old.rename(new_dir / "providers.yaml")


def _rollback_config_layout_v2(product_path: Path, backup_dir: Path) -> None:
    new = product_path / "config" / "providers" / "providers.yaml"
    old = product_path / "config" / "providers.yaml"
    if new.exists() and not old.exists():
        new.rename(old)
        try:
            new.parent.rmdir()
        except OSError:
            pass


register_migration(MigrationStep(
    name="config-layout-v2",
    from_version="0.5.0",
    description="Move providers.yaml to providers/providers.yaml",
    reversible=True,
    execute=_migrate_config_layout_v2,
    rollback=_rollback_config_layout_v2,
))


def _migrate_add_routing_section(product_path: Path, backup_dir: Path) -> None:
    """Add routing section to keprix.yaml if missing."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not available; skipping routing section migration.")
        return

    manifest_path = product_path / "keprix.yaml"
    if not manifest_path.exists():
        return

    manifest = yaml.safe_load(manifest_path.read_text()) or {}
    if "routing" not in manifest.get("features", {}):
        manifest.setdefault("features", {})["routing"] = {
            "enabled": False,
            "combos": False,
            "circuit_breaker": True,
        }
        manifest_path.write_text(yaml.dump(manifest, default_flow_style=False))


register_migration(MigrationStep(
    name="routing-config-v1",
    from_version="0.5.0",
    description="Add routing section to keprix.yaml",
    reversible=True,
    execute=_migrate_add_routing_section,
    rollback=None,   # harmless to leave the section
))


def _migrate_audit_relocation(product_path: Path, backup_dir: Path) -> None:
    """Move audit.db to observability/audit.db if the old path exists."""
    old = product_path / "audit.db"
    obs_dir = product_path / "observability"
    new = obs_dir / "audit.db"
    if old.exists() and not new.exists():
        obs_dir.mkdir(parents=True, exist_ok=True)
        old.rename(new)


def _rollback_audit_relocation(product_path: Path, backup_dir: Path) -> None:
    new = product_path / "observability" / "audit.db"
    old = product_path / "audit.db"
    if new.exists() and not old.exists():
        new.rename(old)


register_migration(MigrationStep(
    name="audit-relocation",
    from_version="0.5.0",
    description="Move audit.db to observability/audit.db",
    reversible=True,
    execute=_migrate_audit_relocation,
    rollback=_rollback_audit_relocation,
))
