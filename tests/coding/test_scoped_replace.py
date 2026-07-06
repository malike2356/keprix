"""Tests for scoped replace operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.coding.scoped_replace import (
    append_to_file,
    apply_edit,
    create_file,
    replace_exact_block,
    rollback_edit,
)


def test_replace_exact_block_hashes_and_diff(tmp_path: Path) -> None:
    repo = tmp_path
    target = repo / "sample.py"
    target.write_text("def hello():\n    return 'old'\n", encoding="utf-8")

    result = replace_exact_block(repo, "sample.py", "return 'old'", "return 'new'")
    assert result.ok
    assert result.old_content_hash != result.new_content_hash
    assert "-    return 'old'" in result.diff_preview
    assert "+    return 'new'" in result.diff_preview

    apply_edit(result, repo)
    assert "return 'new'" in target.read_text(encoding="utf-8")

    rollback_edit(result, repo)
    assert "return 'old'" in target.read_text(encoding="utf-8")


def test_create_and_rollback_file(tmp_path: Path) -> None:
    repo = tmp_path
    result = create_file(repo, "new.txt", "hello\n")
    assert result.ok
    apply_edit(result, repo)
    assert (repo / "new.txt").exists()

    rollback_edit(result, repo)
    assert not (repo / "new.txt").exists()


def test_append_to_file(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "log.txt").write_text("line1\n", encoding="utf-8")
    result = append_to_file(repo, "log.txt", "line2\n")
    assert result.ok
    apply_edit(result, repo)
    assert (repo / "log.txt").read_text(encoding="utf-8") == "line1\nline2\n"


def test_path_outside_repo_blocked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes repo"):
        replace_exact_block(repo, "../outside.txt", "x", "y")
