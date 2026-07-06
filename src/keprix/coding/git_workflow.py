"""Git-native workflow helpers for Aider-style coding UX."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _repo_key(repo_path: Path) -> str:
    return hashlib.sha256(str(repo_path.resolve()).encode("utf-8")).hexdigest()[:16]


def _tracking_dir() -> Path:
    path = Path.home() / ".keprix" / "workspace" / "coding-changes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _tracking_file(repo_path: Path) -> Path:
    return _tracking_dir() / f"{_repo_key(repo_path)}.json"


@dataclass
class GitDiffResult:
    ok: bool
    diff: str
    files: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class GitCommitResult:
    ok: bool
    commit_hash: str | None = None
    message: str = ""
    staged_files: list[str] = field(default_factory=list)
    needs_approval: bool = False
    error: str | None = None


@dataclass
class GitRevertResult:
    ok: bool
    reverted_files: list[str] = field(default_factory=list)
    needs_approval: bool = False
    error: str | None = None


def show_diff(repo_path: Path, files: list[str] | None = None) -> GitDiffResult:
    root = repo_path.resolve()
    cmd = ["git", "-C", str(root), "diff", "--no-color"]
    if files:
        cmd.extend(["--"] + files)
    proc = _run_git(cmd)
    if proc.returncode not in (0, 1):
        return GitDiffResult(ok=False, diff="", error=proc.stderr.strip() or "git diff failed")
    changed = _changed_files(root, files)
    return GitDiffResult(ok=True, diff=proc.stdout, files=changed)


def stage_files(repo_path: Path, files: list[str]) -> GitDiffResult:
    root = repo_path.resolve()
    if not files:
        return GitDiffResult(ok=False, diff="", error="no files to stage")
    proc = _run_git(["git", "-C", str(root), "add", "--"] + files)
    if proc.returncode != 0:
        return GitDiffResult(ok=False, diff="", error=proc.stderr.strip() or "git add failed")
    return show_diff(root, files)


def generate_commit_message(repo_path: Path, files: list[str], issue: str = "") -> str:
    summary = issue.strip().splitlines()[0][:72] if issue.strip() else "Keprix coding session update"
    file_list = ", ".join(files[:5])
    if len(files) > 5:
        file_list += f" (+{len(files) - 5} more)"
    return f"{summary}\n\nFiles: {file_list}\n\nCo-authored-by: Keprix <coding@keprix.local>"


def commit_changes(
    repo_path: Path,
    *,
    message: str,
    files: list[str] | None = None,
    approved: bool = False,
    require_approval: bool = True,
) -> GitCommitResult:
    if require_approval and not approved:
        return GitCommitResult(
            ok=False,
            message=message,
            staged_files=files or [],
            needs_approval=True,
            error="commit requires explicit approval",
        )
    root = repo_path.resolve()
    if files:
        stage = stage_files(root, files)
        if not stage.ok:
            return GitCommitResult(ok=False, error=stage.error)
    proc = _run_git(["git", "-C", str(root), "commit", "-m", message])
    if proc.returncode != 0:
        return GitCommitResult(ok=False, error=proc.stderr.strip() or "git commit failed")
    hash_proc = _run_git(["git", "-C", str(root), "rev-parse", "HEAD"])
    commit_hash = hash_proc.stdout.strip() if hash_proc.returncode == 0 else None
    tracked = files or _changed_files(root)
    _record_keprix_changes(root, tracked, commit_hash)
    return GitCommitResult(ok=True, commit_hash=commit_hash, message=message, staged_files=tracked)


def create_branch(repo_path: Path, branch_name: str) -> GitDiffResult:
    root = repo_path.resolve()
    safe_name = branch_name.replace(" ", "-")[:80]
    proc = _run_git(["git", "-C", str(root), "checkout", "-b", safe_name])
    if proc.returncode != 0:
        return GitDiffResult(ok=False, diff="", error=proc.stderr.strip() or "branch creation failed")
    return GitDiffResult(ok=True, diff=f"Created branch {safe_name}")


def revert_keprix_changes(
    repo_path: Path,
    *,
    approved: bool = False,
    require_approval: bool = True,
) -> GitRevertResult:
    if require_approval and not approved:
        return GitRevertResult(ok=False, needs_approval=True, error="revert requires explicit approval")
    root = repo_path.resolve()
    tracked = _load_keprix_changes(root)
    if not tracked:
        return GitRevertResult(ok=False, error="no keprix-created changes recorded")
    reverted: list[str] = []
    for rel in tracked:
        proc = _run_git(["git", "-C", str(root), "checkout", "--", rel])
        if proc.returncode == 0:
            reverted.append(rel)
    _clear_keprix_changes(root)
    return GitRevertResult(ok=bool(reverted), reverted_files=reverted)


def auto_commit_after_tests(
    repo_path: Path,
    *,
    issue: str,
    files: list[str],
    tests_passed: bool,
    approved: bool = False,
    enabled: bool = False,
) -> GitCommitResult | None:
    if not enabled or not tests_passed:
        return None
    message = generate_commit_message(repo_path, files, issue)
    return commit_changes(repo_path, message=message, files=files, approved=approved, require_approval=True)


def _run_git(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)


def _changed_files(root: Path, files: list[str] | None = None) -> list[str]:
    proc = _run_git(["git", "-C", str(root), "status", "--porcelain"])
    if proc.returncode != 0:
        return list(files or [])
    changed: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        if not files or rel in files:
            changed.append(rel)
    return changed


def track_pending_changes(repo_path: Path, files: list[str]) -> None:
    """Record files touched by Keprix before an explicit commit."""
    _record_keprix_changes(repo_path.resolve(), files, None)


def _record_keprix_changes(root: Path, files: list[str], commit_hash: str | None) -> None:
    path = _tracking_file(root)
    payload = {
        "repo": str(root),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "commit_hash": commit_hash,
        "files": sorted(set(files)),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_keprix_changes(root: Path) -> list[str]:
    path = _tracking_file(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("files", []))
    except Exception:
        return []


def _clear_keprix_changes(root: Path) -> None:
    path = _tracking_file(root)
    if path.exists():
        path.unlink()
