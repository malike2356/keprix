"""Execute and rollback Keprix upgrades for a product."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .history import append_history, get_last_record
from .copy_filters import upgrade_copy_ignore
from .installability import check_target_installable
from .lockfile import record_upgrade
from .manifest import ProductManifest, load_product_manifest, update_tested_against
from .migrations import get_migration_plan, run_migration
from .models import UpgradeRecord
from .versions import version_gte

logger = logging.getLogger(__name__)
Runner = Callable[[list[str], Path | None], subprocess.CompletedProcess[str]]


def _default_runner(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, check=False)


@dataclass
class ExecuteOptions:
    skip_confirmation: bool = False
    force: bool = False
    runner: Runner = _default_runner


class UpgradeExecutor:
    """Runs backup, install, migrate, verify, and history commit for an upgrade."""

    def __init__(
        self,
        manifest: ProductManifest,
        product_path: Path,
        target_version: str,
        installed_version: str,
        options: ExecuteOptions | None = None,
    ):
        self.manifest = manifest
        self.product_path = product_path.expanduser().resolve()
        self.target_version = target_version
        self.installed_version = installed_version
        self.options = options or ExecuteOptions()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.upgrade_dir = self.product_path / ".keprix" / "upgrade"
        self.backup_dir = self.upgrade_dir / "backups" / f"pre-{target_version}-{stamp}"
        self.history_path = self.upgrade_dir / "history.json"
        self.lock_file = self.upgrade_dir / "lock"
        self._lock_held = False
        self.failed_stage: str | None = None
        self.error_message: str = ""

    def execute(self) -> bool:
        self.upgrade_dir.mkdir(parents=True, exist_ok=True)
        start = time.time()
        try:
            if not self._preflight():
                return False
            self.failed_stage = "backup"
            self._backup()
            self.failed_stage = "install"
            if not self._install():
                self._rollback_files_only()
                return False
            self.failed_stage = "migrate"
            if not self._migrate():
                self._rollback_files_only()
                return False
            self.failed_stage = "verify"
            if not self._verify():
                self._rollback_files_only()
                return False
            self._commit(duration_seconds=time.time() - start)
            self.failed_stage = None
            return True
        finally:
            self._release_lock()

    def _preflight(self) -> bool:
        if version_gte(self.installed_version, self.target_version):
            self.failed_stage = "check"
            self.error_message = f"Already on Keprix {self.installed_version}."
            logger.error(self.error_message)
            return False

        usage = shutil.disk_usage(self.product_path)
        if usage.free < 500 * 1024 * 1024 and not self.options.force:
            self.failed_stage = "check"
            self.error_message = "Insufficient disk space (need 500MB)."
            logger.error(self.error_message)
            return False

        if not self.options.force and not self._git_is_clean():
            self.failed_stage = "check"
            self.error_message = "Uncommitted git changes detected. Commit or stash first."
            logger.error(self.error_message)
            return False

        if self.lock_file.exists() and not self.options.force:
            self.failed_stage = "check"
            self.error_message = "Another upgrade is in progress."
            logger.error(self.error_message)
            return False

        installability = check_target_installable(
            self.target_version,
            runner=self.options.runner,
            cwd=self.product_path,
        )
        if not installability.available:
            self.failed_stage = "install"
            self.error_message = installability.recommendation
            logger.error("%s %s", self.error_message, installability.detail)
            return False

        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.write_text(str(datetime.now().isoformat()), encoding="utf-8")
        self._lock_held = True

        if not self.options.skip_confirmation:
            try:
                answer = input(
                    f"\nUpgrade {self.manifest.product_name} to Keprix "
                    f"{self.target_version}? [y/N]: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                self.failed_stage = "check"
                self.error_message = "Upgrade cancelled."
                print("\nCancelled.")
                return False
            if answer not in {"y", "yes"}:
                self.failed_stage = "check"
                self.error_message = "Upgrade cancelled."
                print("Upgrade cancelled.")
                return False
        return True

    def _backup(self) -> None:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.product_path / "keprix.yaml"
        if manifest_path.exists():
            shutil.copy2(manifest_path, self.backup_dir / "keprix.yaml")

        slug_dir = self.product_path / self.manifest.product_slug
        if slug_dir.exists() and slug_dir.is_dir():
            shutil.copytree(
                slug_dir,
                self.backup_dir / self.manifest.product_slug,
                ignore=upgrade_copy_ignore(slug_dir),
            )

        config_dir = self.product_path / "config"
        if config_dir.exists():
            shutil.copytree(config_dir, self.backup_dir / "config", ignore=upgrade_copy_ignore(config_dir))

        billing = self.product_path / "billing.yaml"
        if billing.exists():
            shutil.copy2(billing, self.backup_dir / "billing.yaml")

        (self.backup_dir / "PREVIOUS_KEPRIX_VERSION").write_text(
            self.installed_version, encoding="utf-8"
        )
        freeze = self.options.runner(["pip", "freeze"], self.product_path)
        (self.backup_dir / "pip-freeze.txt").write_text(freeze.stdout, encoding="utf-8")

    def _install(self) -> bool:
        result = self.options.runner(
            ["pip", "install", f"keprix=={self.target_version}"],
            self.product_path,
        )
        if result.returncode != 0:
            self.error_message = f"pip install failed: {(result.stderr or result.stdout).strip()}"
            logger.error(self.error_message)
            return False
        return True

    def _migrate(self) -> bool:
        plan = get_migration_plan(self.installed_version, self.target_version)
        for step in plan.steps:
            try:
                run_migration(step, self.product_path, self.backup_dir)
            except Exception as exc:
                self.error_message = f"Migration {step.name} failed: {exc}"
                logger.error(self.error_message)
                return False
        return True

    def _verify(self) -> bool:
        try:
            import keprix  # noqa: F401
        except ImportError:
            self.error_message = "Keprix import failed after install."
            return False
        try:
            loaded = load_product_manifest(self.product_path / "keprix.yaml")
            if loaded.product_name != self.manifest.product_name:
                self.error_message = "Product manifest verification failed after install."
                return False
        except Exception:
            self.error_message = "Product manifest verification failed after install."
            return False
        return True

    def _commit(self, duration_seconds: float) -> None:
        append_history(
            UpgradeRecord(
                from_version=self.installed_version,
                to_version=self.target_version,
                timestamp=datetime.now().isoformat(),
                backup_path=str(self.backup_dir),
                status="success",
                duration_seconds=duration_seconds,
            ),
            self.history_path,
        )
        update_tested_against(self.product_path / "keprix.yaml", self.target_version)
        record_upgrade(
            self.product_path,
            product=self.manifest.product_slug,
            product_version=self.manifest.product_version,
            from_version=self.installed_version,
            to_version=self.target_version,
            manifest_features=self.manifest.features,
            backup_path=str(self.backup_dir),
        )

    def _rollback_files_only(self) -> None:
        self._restore_from_backup(self.backup_dir)

    def _restore_from_backup(self, backup_dir: Path) -> None:
        manifest_backup = backup_dir / "keprix.yaml"
        if manifest_backup.exists():
            shutil.copy2(manifest_backup, self.product_path / "keprix.yaml")

        slug_backup = backup_dir / self.manifest.product_slug
        slug_target = self.product_path / self.manifest.product_slug
        if slug_backup.exists():
            if slug_target.exists():
                shutil.rmtree(slug_target)
            shutil.copytree(slug_backup, slug_target)

        config_backup = backup_dir / "config"
        config_target = self.product_path / "config"
        if config_backup.exists():
            if config_target.exists():
                shutil.rmtree(config_target)
            shutil.copytree(config_backup, config_target)

        billing_backup = backup_dir / "billing.yaml"
        if billing_backup.exists():
            shutil.copy2(billing_backup, self.product_path / "billing.yaml")

        prev_file = backup_dir / "PREVIOUS_KEPRIX_VERSION"
        if prev_file.exists():
            prev_version = prev_file.read_text(encoding="utf-8").strip()
            self.options.runner(["pip", "install", f"keprix=={prev_version}"], self.product_path)

    def _git_is_clean(self) -> bool:
        if not (self.product_path / ".git").exists():
            return True
        result = self.options.runner(
            ["git", "status", "--porcelain"],
            self.product_path,
        )
        return result.stdout.strip() == ""

    def _release_lock(self) -> None:
        if self._lock_held and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except OSError:
                pass
        self._lock_held = False


def rollback_last_upgrade(
    product_path: Path,
    options: ExecuteOptions | None = None,
) -> bool:
    """Rollback using the most recent successful upgrade record."""
    opts = options or ExecuteOptions()
    root = product_path.expanduser().resolve()
    history_path = root / ".keprix" / "upgrade" / "history.json"
    record = get_last_record(history_path)
    if record is None or record.status != "success":
        logger.error("No successful upgrade to roll back.")
        return False

    manifest = load_product_manifest(root / "keprix.yaml")
    backup_dir = Path(record.backup_path)
    if not backup_dir.exists():
        logger.error("Backup not found: %s", backup_dir)
        return False

    if not opts.skip_confirmation:
        try:
            answer = input(
                f"\nRollback {manifest.product_name} from Keprix {record.to_version} "
                f"to {record.from_version}? [y/N]: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False
        if answer not in {"y", "yes"}:
            print("Rollback cancelled.")
            return False

    executor = UpgradeExecutor(
        manifest=manifest,
        product_path=root,
        target_version=record.to_version,
        installed_version=record.to_version,
        options=opts,
    )
    executor._restore_from_backup(backup_dir)
    update_tested_against(root / "keprix.yaml", record.from_version)
    append_history(
        UpgradeRecord(
            from_version=record.to_version,
            to_version=record.from_version,
            timestamp=datetime.now().isoformat(),
            backup_path=str(backup_dir),
            status="rolled_back",
            duration_seconds=0.0,
        ),
        history_path,
    )
    return True
