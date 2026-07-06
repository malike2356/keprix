"""Tests for git-native coding workflow."""

from __future__ import annotations

import subprocess
from pathlib import Path

from keprix.coding.git_workflow import (
    commit_changes,
    generate_commit_message,
    revert_keprix_changes,
    show_diff,
    stage_files,
    track_pending_changes,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")
    return repo


def test_show_diff_and_stage(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("# Demo\nchanged\n", encoding="utf-8")
    diff = show_diff(repo)
    assert diff.ok
    assert "changed" in diff.diff

    staged = stage_files(repo, ["README.md"])
    assert staged.ok


def test_commit_requires_approval(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("# Demo\nnew\n", encoding="utf-8")
    message = generate_commit_message(repo, ["README.md"], "Update readme")
    result = commit_changes(repo, message=message, files=["README.md"], approved=False, require_approval=True)
    assert not result.ok
    assert result.needs_approval


def test_commit_with_approval(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("# Demo\napproved\n", encoding="utf-8")
    message = generate_commit_message(repo, ["README.md"], "Update readme")
    result = commit_changes(repo, message=message, files=["README.md"], approved=True, require_approval=True)
    assert result.ok
    assert result.commit_hash


def test_revert_keprix_changes_requires_approval(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("# Demo\nkeprix-edit\n", encoding="utf-8")
    track_pending_changes(repo, ["README.md"])

    blocked = revert_keprix_changes(repo, approved=False, require_approval=True)
    assert not blocked.ok
    assert blocked.needs_approval

    reverted = revert_keprix_changes(repo, approved=True, require_approval=True)
    assert reverted.ok
    assert "README.md" in reverted.reverted_files
    assert (repo / "README.md").read_text(encoding="utf-8") == "# Demo\n"
