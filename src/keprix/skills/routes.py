"""Skills HTTP routes for the CE dashboard."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillToggle(BaseModel):
    name: str
    enabled: bool


@router.get("")
async def list_skills() -> list[dict[str, Any]]:
    try:
        from tools.skills_tool import _find_all_skills
        from keprix_cli.skills_config import get_disabled_skills, load_config

        config = load_config()
        disabled = get_disabled_skills(config)
        skills = _find_all_skills(skip_disabled=True)
        for skill in skills:
            skill["enabled"] = skill["name"] not in disabled
        return skills
    except Exception:
        return []


@router.put("/toggle")
async def toggle_skill(body: SkillToggle) -> dict[str, Any]:
    from keprix_cli.skills_config import get_disabled_skills, load_config, save_disabled_skills

    config = load_config()
    disabled = get_disabled_skills(config)
    if body.enabled:
        disabled.discard(body.name)
    else:
        disabled.add(body.name)
    save_disabled_skills(config, disabled)
    return {"ok": True, "name": body.name, "enabled": body.enabled}


@router.get("/content")
async def get_skill_content(name: str) -> dict[str, str]:
    from tools.skill_manager_tool import _find_skill

    found = _find_skill(name)
    if not found:
        raise HTTPException(404, f"Skill '{name}' not found")
    skill_md = found["path"] / "SKILL.md"
    if not skill_md.exists():
        raise HTTPException(404, f"Skill '{name}' has no SKILL.md")
    return {"name": name, "content": skill_md.read_text(encoding="utf-8"), "path": str(skill_md)}
