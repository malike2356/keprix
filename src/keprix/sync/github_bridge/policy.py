"""Policy gates for GitHub agent-sync commits and reads."""

from __future__ import annotations

import os
import re
from pathlib import Path

from keprix.sync.github_bridge.types import DEFAULT_MANIFEST, GithubBridgeManifest

SECRET_CONTENT_PATTERNS = [
    re.compile(r"\b(ghp|gho|ghs|ghr)_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
]


def normalize_repo_rel_path(file_path: str) -> str:
    return file_path.replace("\\", "/").lstrip("./").lstrip("/")


def _glob_to_regexp(glob: str) -> re.Pattern[str]:
    escaped = (
        re.escape(glob)
        .replace(r"\*\*/", ":::DBLSTAR_SLASH:::")
        .replace(r"\*\*", ":::DBLSTAR:::")
        .replace(r"\*", "[^/]*")
        .replace(":::DBLSTAR_SLASH:::", "(?:.*/)?")
        .replace(":::DBLSTAR:::", ".*")
    )
    return re.compile(f"^{escaped}$", re.I)


def path_matches_any_glob(rel_path: str, globs: list[str]) -> bool:
    normalized = normalize_repo_rel_path(rel_path)
    return any(_glob_to_regexp(glob).match(normalized) for glob in globs)


def is_denied_path(rel_path: str, manifest: GithubBridgeManifest | None = None) -> bool:
    manifest = manifest or DEFAULT_MANIFEST
    return path_matches_any_glob(rel_path, manifest.deny_globs)


def is_under_allowed_folder(rel_path: str, allowed_folders: list[str]) -> bool:
    normalized = normalize_repo_rel_path(rel_path)
    for folder in allowed_folders:
        folder_norm = normalize_repo_rel_path(folder)
        if folder_norm == normalized or normalized.startswith(f"{folder_norm}/"):
            return True
        if os.path.basename(normalized) == folder_norm and "/" not in folder_norm:
            return True
    return False


def is_writable_path(
    rel_path: str,
    write_folders: list[str],
    manifest: GithubBridgeManifest | None = None,
) -> bool:
    manifest = manifest or DEFAULT_MANIFEST
    if is_denied_path(rel_path, manifest):
        return False
    return is_under_allowed_folder(rel_path, write_folders)


def content_looks_secret(content: str) -> bool:
    if not content:
        return False
    return any(pattern.search(content) for pattern in SECRET_CONTENT_PATTERNS)


def looks_like_ephemeral_working_memory(content: str) -> bool:
    text = content.strip()
    if not text:
        return True
    if re.match(r'^\s*\{[\s\S]*"role"\s*:\s*"(user|assistant|tool)"', text, re.I):
        return True
    if re.search(r"\btool_call\b|\btool_result\b|\bfunction_call\b", text, re.I) and len(text) > 400:
        return True
    if re.search(r"\b(conversation transcript|raw chat dump|session transcript)\b", text, re.I):
        return True
    return False


def should_commit_file(
    *,
    rel_path: str,
    content: str,
    allowed_write_folders: list[str],
    manifest: GithubBridgeManifest | None = None,
) -> tuple[bool, str | None]:
    manifest = manifest or DEFAULT_MANIFEST
    if is_denied_path(rel_path, manifest):
        return False, "path denied by policy"
    if not is_writable_path(rel_path, allowed_write_folders, manifest):
        return False, "path outside approved write folders"
    if content_looks_secret(content):
        return False, "content matched secret pattern"
    if looks_like_ephemeral_working_memory(content):
        return False, "content looks like ephemeral working memory"
    return True, None
