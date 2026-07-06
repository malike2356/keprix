"""Generated skill registry reload helper."""

from __future__ import annotations

from pathlib import Path


def reload_generated_skills(skills_dir: Path) -> int:
    """Return count of generated skill files discovered."""
    if not skills_dir.exists():
        return 0
    return len(list(skills_dir.glob("*.skill")))
