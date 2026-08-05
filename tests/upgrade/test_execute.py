"""Tests for upgrade/execute.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

from keprix.upgrade.execute import ExecuteOptions, UpgradeExecutor
from keprix.upgrade.manifest import load_product_manifest


def _manifest_file(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "keprix.yaml").write_text(
        """
product:
  name: TestProduct
  slug: testproduct
keprix:
  min_version: "0.2.0"
  tested_against: "0.3.0"
features: {}
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _runner_ok(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if cmd[:2] == ["pip", "install"]:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    if cmd[:2] == ["pip", "freeze"]:
        return subprocess.CompletedProcess(cmd, 0, "keprix==0.3.0\n", "")
    if cmd[:3] == ["git", "status", "--porcelain"]:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.CompletedProcess(cmd, 0, "", "")


def _runner_unavailable(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if cmd[-1:] == ["keprix==0.7.0"] and "--dry-run" in cmd:
        return subprocess.CompletedProcess(
            cmd,
            1,
            "",
            "ERROR: No matching distribution found for keprix==0.7.0\n",
        )
    return _runner_ok(cmd, cwd)


def test_executor_runs_migrations_and_updates_manifest(tmp_path: Path, monkeypatch):
    _manifest_file(tmp_path)
    config = tmp_path / "config"
    config.mkdir()
    (config / "providers.yaml").write_text("providers: []\n", encoding="utf-8")

    manifest = load_product_manifest(tmp_path / "keprix.yaml")
    executor = UpgradeExecutor(
        manifest=manifest,
        product_path=tmp_path,
        target_version="0.7.0",
        installed_version="0.3.0",
        options=ExecuteOptions(skip_confirmation=True, force=True, runner=_runner_ok),
    )
    assert executor.execute() is True
    assert (config / "providers" / "providers.yaml").exists()
    updated = load_product_manifest(tmp_path / "keprix.yaml")
    assert updated.keprix_tested_against == "0.7.0"
    history_path = tmp_path / ".keprix" / "upgrade" / "history.json"
    assert history_path.exists()
    lock_path = tmp_path / ".keprix-lock.yaml"
    assert lock_path.exists()
    lock_data = lock_path.read_text(encoding="utf-8")
    assert "0.7.0" in lock_data


def test_executor_blocks_when_already_on_target(tmp_path: Path):
    _manifest_file(tmp_path)
    manifest = load_product_manifest(tmp_path / "keprix.yaml")
    executor = UpgradeExecutor(
        manifest=manifest,
        product_path=tmp_path,
        target_version="0.3.0",
        installed_version="0.3.0",
        options=ExecuteOptions(skip_confirmation=True, force=True, runner=_runner_ok),
    )
    assert executor.execute() is False


def test_executor_blocks_unavailable_release_before_backup(tmp_path: Path):
    _manifest_file(tmp_path)
    manifest = load_product_manifest(tmp_path / "keprix.yaml")
    executor = UpgradeExecutor(
        manifest=manifest,
        product_path=tmp_path,
        target_version="0.7.0",
        installed_version="0.3.0",
        options=ExecuteOptions(skip_confirmation=True, force=True, runner=_runner_unavailable),
    )
    assert executor.execute() is False
    assert executor.failed_stage == "install"
    assert "not available" in executor.error_message
    assert not (tmp_path / ".keprix" / "upgrade" / "backups").exists()
