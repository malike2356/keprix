"""Tests for repository filemap."""

from __future__ import annotations

from pathlib import Path

from keprix.coding.filemap import build_filemap


def test_filemap_detects_packages_tests_and_configs(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (repo / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "config.yaml").write_text("debug: true\n", encoding="utf-8")

    filemap = build_filemap(repo)
    assert "pyproject.toml" in filemap.packages
    assert "main.py" in filemap.entry_points
    assert any("test_app.py" in path for path in filemap.tests)
    assert "config.yaml" in filemap.configs
    assert "def main" in filemap.symbols.get("main.py", [])
