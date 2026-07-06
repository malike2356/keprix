"""Guardrails for git and repo-scoped operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from keprix.coding.configs import CodingProfile

_DESTRUCTIVE_GIT = re.compile(
    r"\bgit\s+(reset\s+--hard|clean\s+-|checkout\s+\.|push\s+--force|branch\s+-D|rebase)\b",
    re.I,
)
_COMMIT = re.compile(r"\bgit\s+commit\b", re.I)
_PUSH = re.compile(r"\bgit\s+push\b", re.I)


@dataclass
class ReviewDecision:
    allowed: bool
    needs_approval: bool
    reason: str


def path_in_repo(path: Path, repo_root: Path) -> bool:
    try:
        path.resolve().relative_to(repo_root.resolve())
        return True
    except ValueError:
        return False


def review_git_command(command: str, profile: CodingProfile) -> ReviewDecision:
    if _DESTRUCTIVE_GIT.search(command):
        if profile.allow_destructive_git:
            return ReviewDecision(True, True, "destructive git requires approval")
        return ReviewDecision(False, False, "destructive git blocked by profile")
    if _COMMIT.search(command):
        if profile.allow_commit:
            return ReviewDecision(True, True, "commit requires approval")
        return ReviewDecision(False, False, "commit blocked by profile")
    if _PUSH.search(command):
        if profile.allow_push:
            return ReviewDecision(True, True, "push requires approval")
        return ReviewDecision(False, False, "push blocked by profile")
    return ReviewDecision(True, False, "allowed")


def review_file_edit(rel_path: str, repo_root: Path) -> ReviewDecision:
    target = (repo_root / rel_path).resolve()
    if not path_in_repo(target, repo_root.resolve()):
        return ReviewDecision(False, False, "path outside repo")
    return ReviewDecision(True, False, "allowed")


def review_run(profile: CodingProfile, *, edits_count: int, human_approved: bool = False) -> ReviewDecision:
    if edits_count > profile.max_files_per_run:
        return ReviewDecision(False, False, "too many files in run")
    if profile.require_human_review and not human_approved:
        return ReviewDecision(False, True, "human review required")
    return ReviewDecision(True, False, "allowed")
