"""Path and one-writer policy for Syncthing vs agent-sync."""

from __future__ import annotations

from pathlib import Path

from keprix.sync.syncthing.types import FORBIDDEN_PATH_MARKERS, ONE_WRITER_RULES, WriterRole


def normalize_path(path: str) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def paths_overlap(a: str | Path, b: str | Path) -> bool:
    try:
        left = normalize_path(str(a))
        right = normalize_path(str(b))
    except OSError:
        return False
    if left == right:
        return True
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def is_forbidden_syncthing_path(vault_path: str) -> tuple[bool, str | None]:
    text = str(normalize_path(vault_path)).replace("\\", "/")
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in text:
            return True, f"vault_path overlaps agent-sync territory ({marker})"
    return False, None


def validate_separation(*, vault_path: str, agent_sync_clone: str | None) -> list[str]:
    warnings: list[str] = []
    denied, reason = is_forbidden_syncthing_path(vault_path)
    if denied and reason:
        warnings.append(reason)
    if agent_sync_clone and paths_overlap(vault_path, agent_sync_clone):
        warnings.append(
            "Obsidian vault path overlaps GitHub agent-sync clone. "
            "Use Syncthing for vault only; keep agent-sync on memory/skills."
        )
    return warnings


def one_writer_guidance(role: WriterRole) -> dict:
    return dict(ONE_WRITER_RULES.get(role) or ONE_WRITER_RULES["home"])
