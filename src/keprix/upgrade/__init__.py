"""Keprix upgrade system: check, plan, migrate, and history."""

from .alerts import UpgradeAlert, UpgradeAlertPreferences, UpgradeAlertStore, severity_meets_minimum
from .changelog import ChangelogRelease, entries_between, load_changelog, parse_changelog, release_versions
from .discovery import FEATURE_REGISTRY, FeatureDiscovery, FeatureInfo
from .lockfile import ProductLockFile, load_lockfile, record_upgrade, write_lockfile
from .check import UpgradeManifestInfo, check_upgrade, classify_risk
from .context import UpgradeContext, installed_keprix_version
from .dry_run import DryRunOptions, dry_run_upgrade
from .execute import ExecuteOptions, UpgradeExecutor, rollback_last_upgrade
from .history import append_history, get_last_record, load_history
from .manifest import ProductManifest, find_product_root, load_product_manifest, update_tested_against
from .migrations import (
    MIGRATIONS,
    MigrationPlan,
    MigrationStep,
    get_migration_plan,
    register_migration,
    run_migration,
    run_rollback,
)
from .models import DryRunResult, UpgradeCheckResult, UpgradeRecord
from .plan import UpgradePlan, UpgradePlanStep, build_upgrade_plan
from .prompts import ADOPTION_PROMPTS, apply_adoption_prompt, list_adoption_prompt_details, list_adoption_prompts
from .events import clear_listeners, emit_update_event, on_event
from .notifier import UpdateInfo, UpdateNotifier
from .service import UpgradeService
from .versions import latest_version, sort_versions, version_gt, version_gte, version_lt, version_lte, versions_between

__all__ = [
    "ADOPTION_PROMPTS",
    "ChangelogRelease",
    "FEATURE_REGISTRY",
    "FeatureDiscovery",
    "FeatureInfo",
    "ProductLockFile",
    "DryRunOptions",
    "DryRunResult",
    "ExecuteOptions",
    "MIGRATIONS",
    "MigrationPlan",
    "MigrationStep",
    "ProductManifest",
    "UpgradeAlert",
    "UpgradeAlertPreferences",
    "UpgradeAlertStore",
    "UpgradeCheckResult",
    "UpgradeContext",
    "UpgradeExecutor",
    "UpgradeManifestInfo",
    "UpgradePlan",
    "UpgradePlanStep",
    "UpgradeRecord",
    "UpgradeService",
    "UpdateInfo",
    "UpdateNotifier",
    "append_history",
    "apply_adoption_prompt",
    "build_upgrade_plan",
    "check_upgrade",
    "classify_risk",
    "clear_listeners",
    "dry_run_upgrade",
    "emit_update_event",
    "entries_between",
    "find_product_root",
    "get_last_record",
    "get_migration_plan",
    "installed_keprix_version",
    "latest_version",
    "list_adoption_prompt_details",
    "list_adoption_prompts",
    "load_changelog",
    "load_history",
    "load_lockfile",
    "load_product_manifest",
    "on_event",
    "parse_changelog",
    "record_upgrade",
    "register_migration",
    "release_versions",
    "rollback_last_upgrade",
    "run_migration",
    "run_rollback",
    "severity_meets_minimum",
    "sort_versions",
    "update_tested_against",
    "version_gt",
    "version_gte",
    "version_lt",
    "version_lte",
    "versions_between",
    "write_lockfile",
]
