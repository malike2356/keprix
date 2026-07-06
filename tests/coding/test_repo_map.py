"""Tests for Aider-style repo map."""

from __future__ import annotations

from pathlib import Path

from keprix.coding.repo_map import build_repo_map


def test_repo_map_excludes_gitignore_and_secrets(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / ".gitignore").write_text("ignored/\n*.secret\n", encoding="utf-8")
    ignored_dir = repo / "ignored"
    ignored_dir.mkdir()
    (ignored_dir / "skip.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "credentials.secret").write_text("token=abc\n", encoding="utf-8")
    (repo / "app.py").write_text("import os\n\ndef main():\n    return 1\n", encoding="utf-8")
    (repo / "routes_api.py").write_text("router = 1\n", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_main():\n    assert True\n", encoding="utf-8")

    repo_map = build_repo_map(repo)
    assert "app.py" in repo_map.files
    assert "tests/test_app.py" in repo_map.files
    assert "credentials.secret" not in repo_map.files
    assert not any("ignored/" in path for path in repo_map.files)
    assert repo_map.entries["app.py"].imports == ["os"]
    assert "def main" in repo_map.entries["app.py"].symbols
    assert repo_map.ignored_count >= 2


def test_repo_map_compact_text(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    compact = build_repo_map(repo).compact_text()
    assert "Repo:" in compact
    assert "main.py" in compact
