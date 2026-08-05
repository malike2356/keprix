"""Shared ignore rules for upgrade backups and dry-run sandboxes."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path


UPGRADE_COPY_EXCLUDES = (
    ".git",
    ".hg",
    ".svn",
    ".keprix",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "backups",
    "dist",
    "graphify-out",
    "node_modules",
    "venv",
    "*.pyc",
    "*.pyo",
)

UPGRADE_TOP_LEVEL_EXCLUDES = {
    "1st-plan",
}


def upgrade_copy_ignore(root: Path | str) -> Callable[[str, list[str]], set[str]]:
    """Return ignore callback for upgrade copies rooted at ``root``.

    The upgrade flow needs to preserve product/runtime configuration, not copy
    local research corpora, browser profiles, dependency trees, or generated
    caches. Excluding those keeps backups bounded and avoids volatile files
    disappearing while ``shutil.copytree`` is walking them.
    """

    root_path = Path(root).expanduser().resolve()
    pattern_ignore = shutil.ignore_patterns(*UPGRADE_COPY_EXCLUDES)

    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = set(pattern_ignore(directory, names))
        try:
            current = Path(directory).resolve()
            if current == root_path:
                ignored.update(name for name in names if name in UPGRADE_TOP_LEVEL_EXCLUDES)
        except OSError:
            pass
        return ignored

    return ignore
