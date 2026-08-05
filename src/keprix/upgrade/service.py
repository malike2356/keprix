"""High-level upgrade operations for API and GUI consumers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .changelog import entries_between, load_changelog
from .check import check_upgrade
from .context import UpgradeContext
from .dry_run import DryRunOptions, dry_run_upgrade
from .execute import ExecuteOptions, UpgradeExecutor, rollback_last_upgrade
from .history import load_history
from .notifier import UpdateNotifier
from .plan import build_upgrade_plan
from .versions import version_gt


def resolve_api_product_path(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_path = os.environ.get("KEPRIX_UPGRADE_PRODUCT_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    home = os.environ.get("KEPRIX_HOME", "").strip()
    if home:
        return Path(home).expanduser().resolve()
    return Path.cwd().expanduser().resolve()


class UpgradeService:
    def __init__(self, product_path: Path | None = None):
        self.product_path = resolve_api_product_path(str(product_path) if product_path else None)

    def context(self) -> UpgradeContext:
        return UpgradeContext.resolve(self.product_path, allow_default=True)

    def check(self, target: str | None = None) -> dict[str, Any]:
        ctx = self.context()
        resolved = ctx.resolve_target(target)
        releases = load_changelog(ctx.changelog_path)
        changelog = entries_between(ctx.installed_version, resolved, releases)
        result = check_upgrade(
            ctx.manifest.to_upgrade_info(),
            ctx.installed_version,
            resolved,
            ctx.available_versions,
            changelog=changelog,
            changelog_url=f"https://github.com/malike2356/keprix/releases/tag/v{resolved}",
        )
        return {
            "product": result.product,
            "check": result.to_dict(),
            "full": {
                "breaking_changes": result.breaking_changes,
                "deprecated_features": result.deprecated_features,
                "new_features": result.new_features,
                "config_migrations_required": result.config_migrations_required,
                "changelog_url": result.changelog_url,
                "recommendation": result.recommendation,
            },
            "update_available": ctx.installed_version != resolved,
            "current_version": ctx.installed_version,
            "target_version": resolved,
        }

    def status(self) -> dict[str, Any]:
        notifier = UpdateNotifier(self.product_path)
        store_status = notifier.store.status()
        ctx = self.context()
        alerts = [
            alert
            for alert in store_status.get("alerts", [])
            if version_gt(str(alert.get("target_version") or "0.0.0"), ctx.installed_version)
        ]
        channel = self._release_channel(ctx)
        return {
            "product": ctx.manifest.product_name,
            "current_version": ctx.installed_version,
            **store_status,
            "alert_count": len(alerts),
            "alerts": alerts,
            **channel,
        }

    def _release_channel(self, ctx: UpgradeContext) -> dict[str, Any]:
        from .installability import check_target_installable

        latest = ctx.resolve_target("latest")
        update_listed = version_gt(latest, ctx.installed_version)
        installability = (
            check_target_installable(latest, cwd=self.product_path)
            if update_listed
            else None
        )
        installable = bool(installability and installability.available)
        if not update_listed:
            channel = "current"
            recommendation = f"Installed Keprix {ctx.installed_version} matches the local changelog."
        elif installable:
            channel = "stable"
            recommendation = f"Keprix {latest} is listed and installable from the package index."
        else:
            channel = "changelog_only"
            recommendation = (
                installability.recommendation
                if installability
                else f"Keprix {latest} is listed in CHANGELOG.yaml but is not installable yet."
            )
        return {
            "latest_changelog_version": latest,
            "update_listed": update_listed,
            "installable": installable,
            "channel": channel,
            "recommendation": recommendation,
        }

    def plan(self, target: str | None = None) -> dict[str, Any]:
        ctx = self.context()
        resolved = ctx.resolve_target(target)
        releases = load_changelog(ctx.changelog_path)
        plan = build_upgrade_plan(
            ctx.installed_version,
            resolved,
            ctx.available_versions,
            releases=releases,
        )
        return {
            "from_version": plan.from_version,
            "to_version": plan.to_version,
            "step_count": plan.step_count,
            "direct_jump_recommended": plan.direct_jump_recommended,
            "steps": [
                {
                    "from_version": step.from_version,
                    "to_version": step.to_version,
                    "risk": step.risk,
                    "features": step.features,
                    "config_migrations": step.config_migrations,
                    "migration_steps": [
                        {"name": m.name, "description": m.description} for m in step.migration_steps
                    ],
                }
                for step in plan.steps
            ],
        }

    def changelog(self, target: str | None = None) -> dict[str, Any]:
        ctx = self.context()
        resolved = ctx.resolve_target(target)
        releases = load_changelog(ctx.changelog_path)
        entries = entries_between(ctx.installed_version, resolved, releases)
        return {
            "from_version": ctx.installed_version,
            "to_version": resolved,
            "entries": entries,
        }

    def history(self) -> dict[str, Any]:
        path = self.product_path / ".keprix" / "upgrade" / "history.json"
        records = load_history(path)
        return {
            "records": [
                {
                    "from_version": record.from_version,
                    "to_version": record.to_version,
                    "timestamp": record.timestamp,
                    "status": record.status,
                    "backup_path": record.backup_path,
                    "duration_seconds": record.duration_seconds,
                }
                for record in records
            ]
        }

    def dry_run(self, target: str, *, skip_tests: bool = False) -> dict[str, Any]:
        ctx = self.context()
        resolved = ctx.resolve_target(target)
        result = dry_run_upgrade(
            ctx.manifest.product_name,
            resolved,
            ctx.product_path,
            options=DryRunOptions(skip_tests=skip_tests),
        )
        return {
            "product": result.product,
            "target_version": result.target_version,
            "passed": result.passed,
            "total_tests": result.total_tests,
            "passed_tests": result.passed_tests,
            "failed_tests": result.failed_tests,
            "warnings": result.warnings,
            "failed_test_details": result.failed_test_details,
            "duration_seconds": result.duration_seconds,
            "recommendation": result.recommendation,
        }

    def execute(self, target: str, *, force: bool = False) -> dict[str, Any]:
        ctx = self.context()
        resolved = ctx.resolve_target(target)
        executor = UpgradeExecutor(
            manifest=ctx.manifest,
            product_path=ctx.product_path,
            target_version=resolved,
            installed_version=ctx.installed_version,
            options=ExecuteOptions(skip_confirmation=force, force=force),
        )
        ok = executor.execute()
        return {
            "success": ok,
            "target_version": resolved,
            "product": ctx.manifest.product_name,
            "stage": executor.failed_stage,
            "error": executor.error_message,
        }

    def rollback(self, *, force: bool = False) -> dict[str, Any]:
        ok = rollback_last_upgrade(
            self.product_path,
            options=ExecuteOptions(skip_confirmation=force, force=force),
        )
        ctx = self.context()
        return {"success": ok, "current_version": ctx.installed_version}

    def wizard_steps(self, target: str) -> list[dict[str, Any]]:
        check = self.check(target)
        availability = self.dry_run(target, skip_tests=True)
        steps = [
            {
                "id": "check",
                "label": "Compatibility check",
                "status": "done" if check["check"]["compatible"] else "failed",
                "detail": check["check"]["recommendation"],
            },
            {
                "id": "availability",
                "label": "Install availability",
                "status": "done" if availability["passed"] else "failed",
                "detail": (
                    f"Keprix {availability['target_version']} can be installed."
                    if availability["passed"]
                    else availability["recommendation"]
                ),
            },
            {
                "id": "tests",
                "label": "Test suite",
                "status": "pending" if availability["passed"] else "failed",
                "detail": (
                    "Runs when you start the upgrade."
                    if availability["passed"]
                    else "Not run because the target package is unavailable."
                ),
            },
            {"id": "backup", "label": "Backup", "status": "pending", "detail": "Runs during execute"},
            {"id": "install", "label": "Install", "status": "pending", "detail": ""},
            {"id": "migrate", "label": "Migrate config", "status": "pending", "detail": ""},
            {"id": "verify", "label": "Verify", "status": "pending", "detail": ""},
        ]
        return steps
