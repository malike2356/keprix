"""Built app registry tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.built_apps.manifest import load_built_app_manifest
from keprix.built_apps.registry import list_installed_apps_summary

ROOT = Path(__file__).resolve().parents[2]


def test_load_sample_manifest() -> None:
    manifest = load_built_app_manifest(ROOT / "examples/built-app-starter/built_app.yaml")
    assert manifest.id == "starter"
    assert manifest.navigation
    assert manifest.navigation.items[1].href == "/apps/starter/reports"


def test_reject_manifest_href_outside_prefix(tmp_path: Path) -> None:
    manifest_path = tmp_path / "built_app.yaml"
    manifest_path.write_text(
        """
id: bad
label: Bad
entry: /apps/bad
navigation:
  items:
    - id: escape
      label: Escape
      href: /admin
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="navigation href"):
        load_built_app_manifest(manifest_path)


def test_list_summary_excludes_navigation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    app_dir = tmp_path / "built_apps" / "starter"
    app_dir.mkdir(parents=True)
    app_dir.joinpath("built_app.yaml").write_text(
        (ROOT / "examples/built-app-starter/built_app.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    apps = list_installed_apps_summary()
    assert apps[0]["id"] == "starter"
    assert "navigation" not in apps[0]
