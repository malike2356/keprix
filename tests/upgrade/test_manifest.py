"""Tests for upgrade/manifest.py and upgrade/context.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.upgrade.context import UpgradeContext
from keprix.upgrade.manifest import find_product_root, load_product_manifest, update_tested_against


def _write_manifest(root: Path, tested_against: str = "0.3.0") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "keprix.yaml").write_text(
        f"""
product:
  name: TestProduct
  slug: testproduct
keprix:
  min_version: "0.2.0"
  tested_against: "{tested_against}"
  incompatible_with: ["0.8.0"]
features:
  billing:
    enabled: false
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_load_product_manifest(tmp_path: Path):
    _write_manifest(tmp_path)
    manifest = load_product_manifest(tmp_path / "keprix.yaml")
    assert manifest.product_name == "TestProduct"
    assert manifest.product_slug == "testproduct"
    assert manifest.keprix_tested_against == "0.3.0"
    assert manifest.keprix_incompatible_with == ["0.8.0"]


def test_find_product_root_searches_upward(tmp_path: Path):
    nested = tmp_path / "apps" / "demo"
    _write_manifest(tmp_path)
    nested.mkdir(parents=True)
    assert find_product_root(nested) == tmp_path.resolve()


def test_update_tested_against(tmp_path: Path):
    _write_manifest(tmp_path, tested_against="0.3.0")
    path = tmp_path / "keprix.yaml"
    update_tested_against(path, "0.7.0")
    manifest = load_product_manifest(path)
    assert manifest.keprix_tested_against == "0.7.0"


def test_upgrade_context_resolve(tmp_path: Path, monkeypatch):
    _write_manifest(tmp_path)
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.3.0")
    ctx = UpgradeContext.resolve(tmp_path)
    assert ctx.manifest.product_name == "TestProduct"
    assert ctx.installed_version == "0.3.0"
    assert "0.7.0" in ctx.available_versions


def test_upgrade_context_resolve_target_latest(tmp_path: Path, monkeypatch):
    _write_manifest(tmp_path)
    monkeypatch.setattr("keprix.upgrade.context.installed_keprix_version", lambda: "0.3.0")
    ctx = UpgradeContext.resolve(tmp_path)
    assert ctx.resolve_target("latest") == "0.16.0"


def test_find_product_root_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        find_product_root(tmp_path)
