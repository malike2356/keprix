"""Tests for productivity integration skills (prompt 175)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_SKILLS = PROJECT_ROOT / "src" / "keprix" / "skills"
PLAYBOOK_PATH = PROJECT_ROOT / "examples" / "productivity" / "notion-trello-sync" / "playbook.yaml"


def _skill_md(skill_name: str) -> Path:
    matches = list(BUNDLED_SKILLS.rglob(f"productivity/{skill_name}/SKILL.md"))
    assert len(matches) == 1, f"Expected one SKILL.md for {skill_name}, found {len(matches)}"
    return matches[0]


def _parse_skill_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    assert end != -1, f"Missing closing frontmatter in {path}"
    return yaml.safe_load(text[3:end]) or {}


@pytest.mark.parametrize("skill_name", ["trello", "productivity-integrations", "notion"])
def test_productivity_skill_frontmatter(skill_name: str):
    meta = _parse_skill_frontmatter(_skill_md(skill_name))
    assert meta.get("name") == skill_name
    assert meta.get("description")


def test_bundled_discovery_includes_new_productivity_skills():
    from keprix_constants import get_bundled_skills_dir
    from tools.skills_sync import _discover_bundled_skills

    bundled_dir = get_bundled_skills_dir(BUNDLED_SKILLS)
    names = {name for name, _ in _discover_bundled_skills(bundled_dir)}
    assert "trello" in names
    assert "productivity-integrations" in names
    assert "notion" in names


def test_find_all_skills_lists_trello_and_productivity_integrations(monkeypatch):
    import agent.skill_utils as skill_utils_mod
    import tools.skills_tool as skills_tool_mod

    monkeypatch.setattr(skills_tool_mod, "SKILLS_DIR", BUNDLED_SKILLS)
    monkeypatch.setattr(skill_utils_mod, "get_external_skills_dirs", lambda: [])
    monkeypatch.setattr(skills_tool_mod, "_get_disabled_skill_names", lambda: set())

    from tools.skills_tool import _find_all_skills

    names = {skill["name"] for skill in _find_all_skills()}
    assert "trello" in names
    assert "productivity-integrations" in names


def test_notion_trello_sync_playbook_yaml_parses():
    assert PLAYBOOK_PATH.is_file(), f"Missing playbook: {PLAYBOOK_PATH}"
    data = yaml.safe_load(PLAYBOOK_PATH.read_text(encoding="utf-8"))
    assert data["name"] == "notion-trello-weekly-sync"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["id"] == "list_cards"
    assert data["variables"]["board_id"] == ""
