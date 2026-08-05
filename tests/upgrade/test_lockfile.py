"""Tests for upgrade/lockfile.py."""

from __future__ import annotations

from pathlib import Path

import yaml

from keprix.upgrade.lockfile import load_lockfile, record_upgrade, write_lockfile


def test_record_upgrade_creates_lockfile(tmp_path: Path):
    lock = record_upgrade(
        tmp_path,
        product="testproduct",
        product_version="1.0.0",
        from_version="0.3.0",
        to_version="0.7.0",
        manifest_features={"billing": {"enabled": True}},
        backup_path=str(tmp_path / "backup"),
    )
    assert lock.keprix_version == "0.7.0"
    assert lock.last_upgrade_from == "0.3.0"
    assert lock.features["billing"]["enabled"] is True
    path = tmp_path / ".keprix-lock.yaml"
    assert path.exists()
    loaded = load_lockfile(path)
    assert loaded is not None
    assert loaded.keprix_version == "0.7.0"
    assert len(loaded.backups) == 1


def test_load_lockfile_invalid_returns_none(tmp_path: Path):
    path = tmp_path / ".keprix-lock.yaml"
    path.write_text("not: [valid", encoding="utf-8")
    assert load_lockfile(path) is None


def test_write_lockfile_round_trip(tmp_path: Path):
    path = tmp_path / ".keprix-lock.yaml"
    lock = record_upgrade(
        tmp_path,
        product="demo",
        product_version="2.0.0",
        from_version="0.5.0",
        to_version="0.6.0",
    )
    write_lockfile(lock, path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["product"] == "demo"
    assert data["keprix_version"] == "0.6.0"
