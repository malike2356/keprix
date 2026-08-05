"""Git helpers for the agent-sync clone."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class GitBridgeError(RuntimeError):
    pass


def redact_git_secrets(text: str, token: str | None = None) -> str:
    out = text
    if token:
        out = out.replace(token, "[redacted]")
    import re

    return re.sub(r"x-access-token:[^@\s]+@", "x-access-token:[redacted]@", out, flags=re.I)


def _run_git(args: list[str], *, cwd: Path | None = None, timeout_s: int = 120) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitBridgeError(f"git {args[0]} timed out") from exc
    if completed.returncode != 0:
        raise GitBridgeError(
            f"git {' '.join(args)} failed ({completed.returncode}): {(completed.stderr or completed.stdout).strip()}"
        )
    return completed.stdout


def remote_url(owner: str, repo: str, token: str) -> str:
    from urllib.parse import quote

    return f"https://x-access-token:{quote(token, safe='')}@github.com/{owner}/{repo}.git"


def ensure_clone(*, owner: str, repo: str, branch: str, token: str, local_path: Path) -> dict[str, bool]:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if (local_path / ".git").exists():
        try:
            _run_git(["remote", "set-url", "origin", remote_url(owner, repo, token)], cwd=local_path)
        except GitBridgeError as exc:
            raise GitBridgeError(redact_git_secrets(str(exc), token)) from exc
        return {"cloned": False}
    if local_path.exists():
        shutil.rmtree(local_path)
    try:
        _run_git(
            ["clone", "--branch", branch, "--single-branch", remote_url(owner, repo, token), str(local_path)],
            timeout_s=180,
        )
    except GitBridgeError as exc:
        raise GitBridgeError(redact_git_secrets(str(exc), token)) from exc
    return {"cloned": True}


def pull_rebase(*, local_path: Path, branch: str, token: str, owner: str, repo: str) -> None:
    try:
        _run_git(["remote", "set-url", "origin", remote_url(owner, repo, token)], cwd=local_path)
        _run_git(["fetch", "origin", branch], cwd=local_path)
        try:
            _run_git(["checkout", branch], cwd=local_path)
        except GitBridgeError:
            _run_git(["checkout", "-B", branch, f"origin/{branch}"], cwd=local_path)
        _run_git(["pull", "--rebase", "origin", branch], cwd=local_path)
    except GitBridgeError as exc:
        raise GitBridgeError(redact_git_secrets(str(exc), token)) from exc


def commit_and_push(
    *,
    local_path: Path,
    branch: str,
    token: str,
    owner: str,
    repo: str,
    message: str,
    paths: list[str],
) -> dict[str, bool]:
    if not paths:
        return {"pushed": False, "committed": False}
    try:
        _run_git(["remote", "set-url", "origin", remote_url(owner, repo, token)], cwd=local_path)
        _run_git(["add", "--", *paths], cwd=local_path)
        status = _run_git(["status", "--porcelain"], cwd=local_path)
        if not status.strip():
            return {"pushed": False, "committed": False}
        _run_git(
            [
                "-c",
                "user.name=Keprix Agent Sync",
                "-c",
                "user.email=agent-sync@keprix.local",
                "commit",
                "-m",
                message,
            ],
            cwd=local_path,
        )
        _run_git(["push", "origin", f"HEAD:{branch}"], cwd=local_path)
        return {"pushed": True, "committed": True}
    except GitBridgeError as exc:
        raise GitBridgeError(redact_git_secrets(str(exc), token)) from exc


def list_tracked_files(local_path: Path) -> list[str]:
    stdout = _run_git(["ls-files"], cwd=local_path)
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def git_diff_names(local_path: Path) -> list[str]:
    try:
        stdout = _run_git(["diff", "--name-only", "HEAD"], cwd=local_path)
    except GitBridgeError:
        return []
    from keprix.sync.github_bridge.policy import normalize_repo_rel_path

    return [normalize_repo_rel_path(line.strip()) for line in stdout.splitlines() if line.strip()]
