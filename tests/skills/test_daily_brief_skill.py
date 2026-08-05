"""Personal OS daily-brief skill lint."""

from __future__ import annotations

from pathlib import Path


def test_daily_brief_skill_readiness_and_description() -> None:
    text = Path("packages/packs/keprix-personal-os-starter/skills/daily-brief/SKILL.md").read_text(encoding="utf-8")
    assert "description: Daily calendar tasks and memory brief" in text
    assert len("Daily calendar tasks and memory brief") <= 60
    assert "readiness note" in text
