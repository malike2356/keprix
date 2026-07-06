"""Tests for issue-to-patch runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.coding.issue_runner import IssueRunRequest, run_issue
from keprix.coding.review import review_git_command
from keprix.coding.configs import load_profile


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    (repo / "app.py").write_text("VALUE = 'old'\n", encoding="utf-8")
    return repo


def test_issue_runner_appends_marker(sample_repo: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path / "trajectories",
    )
    result = run_issue(
        IssueRunRequest(
            issue="Add marker comment to README.md",
            repo_path=sample_repo,
            profile="default",
        )
    )
    assert result.ok
    assert "Keprix coding marker" in (sample_repo / "README.md").read_text(encoding="utf-8")
    assert result.patch
    assert Path(result.trajectory_path).exists()


def test_exact_replace_in_issue(sample_repo: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path / "trajectories",
    )
    result = run_issue(
        IssueRunRequest(
            issue="Replace 'old' with 'new' in app.py",
            repo_path=sample_repo,
            profile="default",
        )
    )
    assert result.ok
    assert "VALUE = 'new'" in (sample_repo / "app.py").read_text(encoding="utf-8")


def test_human_review_blocks_without_approval(sample_repo: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path / "trajectories",
    )
    result = run_issue(
        IssueRunRequest(
            issue="Add marker to README.md",
            repo_path=sample_repo,
            profile="human_review",
            human_approved=False,
        )
    )
    assert not result.ok
    assert result.error == "human review required"


def test_tests_failure_rolls_back(sample_repo: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "keprix.coding.trajectory._trajectory_dir",
        lambda: tmp_path / "trajectories",
    )
    before = (sample_repo / "README.md").read_text(encoding="utf-8")
    result = run_issue(
        IssueRunRequest(
            issue="Add marker to README.md",
            repo_path=sample_repo,
            profile="default",
            test_command="exit 1",
        )
    )
    assert not result.ok
    assert (sample_repo / "README.md").read_text(encoding="utf-8") == before


def test_destructive_git_blocked_by_profile() -> None:
    profile = load_profile("locked_down")
    decision = review_git_command("git reset --hard HEAD", profile)
    assert not decision.allowed
