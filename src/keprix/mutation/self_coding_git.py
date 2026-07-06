"""Git branch merge and rollback helpers for code mutations (Prompt 153)."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GitCommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    commit_hash: str | None = None


def _run_git(repo_root: Path, args: list[str], *, timeout: int = 120) -> GitCommandResult:
    cmd = ["git", "-C", str(repo_root.resolve())] + args
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
        commit_hash = None
        if proc.returncode == 0 and args and args[0] == "commit":
            head = _run_git(repo_root, ["rev-parse", "HEAD"])
            if head.ok:
                commit_hash = head.stdout.strip()
        return GitCommandResult(
            ok=proc.returncode == 0,
            stdout=(proc.stdout or "").strip(),
            stderr=(proc.stderr or "").strip(),
            commit_hash=commit_hash,
        )
    except Exception as exc:
        return GitCommandResult(ok=False, stderr=str(exc))


def current_branch(repo_root: Path) -> str | None:
    result = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout if result.ok else None


def create_branch(repo_root: Path, branch_name: str) -> GitCommandResult:
    safe = branch_name.replace(" ", "-")[:120]
    return _run_git(repo_root, ["checkout", "-b", safe])


def delete_branch(repo_root: Path, branch_name: str, *, checkout: str | None = None) -> GitCommandResult:
    base = checkout or current_branch(repo_root) or "main"
    if current_branch(repo_root) == branch_name:
        switched = _run_git(repo_root, ["checkout", base])
        if not switched.ok:
            return switched
    return _run_git(repo_root, ["branch", "-D", branch_name])


def merge_mutation_branch(
    repo_root: Path,
    branch_name: str,
    *,
    strategy: str = "squash",
    message: str = "Merge scoped code mutation",
) -> GitCommandResult:
    base = current_branch(repo_root) or "main"
    if base == branch_name:
        checkout_main = _run_git(repo_root, ["checkout", "main"])
        if not checkout_main.ok:
            checkout_main = _run_git(repo_root, ["checkout", "master"])
        if not checkout_main.ok:
            return checkout_main
        base = current_branch(repo_root) or "main"

    if strategy == "no-ff":
        merged = _run_git(repo_root, ["merge", "--no-ff", branch_name, "-m", message])
        if not merged.ok:
            return merged
        head = _run_git(repo_root, ["rev-parse", "HEAD"])
        return GitCommandResult(ok=True, stdout=merged.stdout, commit_hash=head.stdout.strip() if head.ok else None)

    squashed = _run_git(repo_root, ["merge", "--squash", branch_name])
    if not squashed.ok:
        return squashed
    committed = _run_git(repo_root, ["commit", "-m", message])
    return committed


def revert_merge_commit(repo_root: Path, commit_hash: str) -> GitCommandResult:
    return _run_git(repo_root, ["revert", "--no-edit", "-m", "1", commit_hash])


def revert_or_delete_mutation_branch(
    repo_root: Path,
    branch_name: str,
    *,
    merged: bool,
    merge_commit_hash: str | None,
) -> GitCommandResult:
    if merged and merge_commit_hash:
        reverted = revert_merge_commit(repo_root, merge_commit_hash)
        if reverted.ok:
            delete_branch(repo_root, branch_name)
        return reverted
    return delete_branch(repo_root, branch_name)
