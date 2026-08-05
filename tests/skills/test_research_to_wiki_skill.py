"""Personal OS research-to-wiki skill lint."""

from __future__ import annotations

from pathlib import Path


def test_research_to_wiki_skill_mentions_vault_fallback() -> None:
    text = Path("packages/packs/keprix-personal-os-starter/skills/research-to-wiki/SKILL.md").read_text(encoding="utf-8")
    assert len("Turn raw research into wiki notes") <= 60
    assert "no vault is configured" in text
    assert "wikilinks" in text
