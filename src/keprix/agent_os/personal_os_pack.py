"""Install helpers for the official Personal OS starter pack."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from keprix.agent_os.audit_seed_importer import import_audit_seed
from keprix.agent_os.action_board_store import ActionBoardStore
from keprix.workspace.template_presets import create_workspace
from keprix_constants import get_keprix_home

PACK_ID = "keprix-personal-os-starter"


def apply_personal_os_pack(pack_dir: Path, *, user_id: str = "default") -> dict[str, Any]:
    home = get_keprix_home()
    copied = {"skills": 0, "agent_apps": 0, "audit_id": None, "pins": 0}
    for skill_dir in sorted((pack_dir / "skills").iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        target = home / "skills" / skill_dir.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill_dir, target)
        copied["skills"] += 1
    apps_root = pack_dir / "agent-apps"
    if apps_root.exists():
        for app_dir in sorted(apps_root.iterdir()):
            if not (app_dir / "agent.yaml").is_file():
                continue
            target = home / "agent-apps" / app_dir.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(app_dir, target)
            copied["agent_apps"] += 1
    connections = pack_dir / "connections.md.tpl"
    if connections.exists():
        target = home / "workspaces" / "personal-os" / "connections.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(connections, target)
    create_workspace("personal-os", "knowledge_pipeline")
    seed = pack_dir / "audit-seed.json"
    if seed.exists():
        copied["audit_id"] = import_audit_seed(seed, user_id=user_id).audit_id
    store = ActionBoardStore()
    for skill in ("daily-brief", "inbox-triage", "research-to-wiki"):
        store.add_pin(user_id, action_type="skill", action_id=skill, label=skill.replace("-", " ").title())
        copied["pins"] += 1
    return copied
