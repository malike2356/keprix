"""Personal OS inbox-triage skill lint."""

from __future__ import annotations

from pathlib import Path


def test_inbox_triage_skill_degrades_without_email() -> None:
    text = Path("packages/packs/keprix-personal-os-starter/skills/inbox-triage/SKILL.md").read_text(encoding="utf-8")
    assert len("Email triage and reply draft workflow") <= 60
    assert "email is not configured" in text
    assert "Never send mail automatically" in text
