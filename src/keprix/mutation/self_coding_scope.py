"""Hardcoded allowlist for scoped self-coding mutation (Prompt 153)."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

MUTATION_ALLOWED_PATHS: list[str] = [
    "src/keprix/tools/",
    "src/keprix/skills/",
    "src/keprix/playbooks/",
    "src/keprix/personas/",
    "src/keprix/plugins/",
    "src/keprix/optional-skills/",
]

MUTATION_FORBIDDEN_PATHS: list[str] = [
    "src/keprix/security/",
    "src/keprix/vault/",
    "src/keprix/auth/",
    "src/keprix/review_gateway/",
    "src/keprix/billing/",
    "src/keprix/governance/",
    "src/keprix/pack_gate/",
    "migrations/",
    "src/keprix/db/",
]


def _normalize_path(path: str) -> str:
    cleaned = path.strip().replace("\\", "/")
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned and not cleaned.endswith("/") and "." not in PurePosixPath(cleaned).name:
        cleaned += "/"
    return cleaned


def get_allowed_repo_root_relative_paths() -> list[str]:
    """Return MUTATION_ALLOWED_PATHS for repo_map scoping."""
    return list(MUTATION_ALLOWED_PATHS)


def is_path_in_mutation_scope(rel_path: str) -> bool:
    """Return True when rel_path is under an allowed prefix and not forbidden."""
    norm = rel_path.strip().replace("\\", "/").lstrip("./")
    for forbidden in MUTATION_FORBIDDEN_PATHS:
        forbidden_norm = forbidden.rstrip("/")
        if norm == forbidden_norm or norm.startswith(forbidden):
            return False
    for allowed in MUTATION_ALLOWED_PATHS:
        allowed_norm = allowed.rstrip("/")
        if norm == allowed_norm or norm.startswith(allowed):
            return True
    return False


def is_allowed_target_dir(target_dir: str) -> bool:
    norm = _normalize_path(target_dir)
    for allowed in MUTATION_ALLOWED_PATHS:
        allowed_norm = _normalize_path(allowed)
        if norm == allowed_norm or norm.startswith(allowed_norm):
            return True
    return False


def _parse_diff_paths(diff_text: str) -> list[str]:
    paths: set[str] = set()
    for line in diff_text.splitlines():
        if not (line.startswith("+++ ") or line.startswith("--- ")):
            continue
        raw = line[4:].strip()
        if raw == "/dev/null":
            continue
        if raw.startswith("a/") or raw.startswith("b/"):
            raw = raw[2:]
        if "\t" in raw:
            raw = raw.split("\t", 1)[0]
        paths.add(raw)
    return sorted(paths)


def validate_diff_scope(diff_text: str) -> tuple[bool, list[str]]:
    """Validate every path in a unified diff against the mutation allowlist."""
    try:
        if not diff_text or not diff_text.strip():
            return False, ["empty diff"]
        violations: list[str] = []
        for path in _parse_diff_paths(diff_text):
            if not is_path_in_mutation_scope(path):
                violations.append(path)
        return (len(violations) == 0, violations)
    except Exception:
        return False, ["diff parse error"]
