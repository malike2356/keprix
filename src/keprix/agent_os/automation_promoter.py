"""Promote approved skills into cron, playbook, or Agent App automations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from keprix.agent_os.automation_link_store import AutomationLinkStore
from keprix.agent_os.templates.agent_app_from_skill import agent_app_manifest
from keprix.agent_os.templates.cron_from_skill import cron_spec
from keprix.agent_os.templates.playbook_from_skill import playbook_document
from keprix.playbook.yaml_compiler import compile_playbook_document
from keprix_constants import get_keprix_home


def _skill_path(skill_slug: str) -> Path:
    return get_keprix_home() / "skills" / skill_slug / "SKILL.md"


def _require_skill(skill_slug: str) -> None:
    if not _skill_path(skill_slug).is_file():
        raise FileNotFoundError(f"Skill not found: {skill_slug}")


class AutomationPromoter:
    def __init__(self, links: AutomationLinkStore | None = None) -> None:
        self.links = links or AutomationLinkStore()

    def promote(
        self,
        *,
        skill_slug: str,
        target: str,
        schedule: str | None = None,
        name: str | None = None,
        deliver_to: str | None = None,
    ) -> dict[str, Any]:
        _require_skill(skill_slug)
        if target == "cron":
            return self._promote_cron(skill_slug, schedule=schedule or "0 8 * * 1-5", name=name, deliver_to=deliver_to or "local")
        if target == "playbook":
            return self._promote_playbook(skill_slug, name=name)
        if target == "agent_app":
            return self._promote_agent_app(skill_slug, name=name, schedule=schedule)
        raise ValueError(f"Unsupported promotion target: {target}")

    def links_for_skill(self, skill_slug: str) -> list[dict[str, Any]]:
        return [link.to_dict() for link in self.links.list(skill_slug=skill_slug)]

    def remove_link(self, automation_type: str, automation_id: str) -> int:
        return self.links.remove(automation_type, automation_id)

    def _promote_cron(self, skill_slug: str, *, schedule: str, name: str | None, deliver_to: str) -> dict[str, Any]:
        from keprix.cron.jobs import create_job

        spec = cron_spec(skill_slug, name=name, schedule=schedule, deliver_to=deliver_to)
        job = create_job(
            prompt=spec["prompt"],
            schedule=spec["schedule"],
            name=spec["name"],
            deliver=spec["deliver_to"],
            skills=spec["skills"],
            origin={"source": "agent_os_promoter", "skill": skill_slug},
        )
        link = self.links.add(
            skill_slug=skill_slug,
            automation_type="cron",
            automation_id=str(job["id"]),
            edit_url="/admin/cron",
            metadata={"schedule": schedule, "deliver_to": deliver_to},
        )
        return {"automation_type": "cron", "id": job["id"], "edit_url": link.edit_url, "link": link.to_dict(), "artifact": job}

    def _promote_playbook(self, skill_slug: str, *, name: str | None) -> dict[str, Any]:
        document = playbook_document(skill_slug, name=name)
        compiled = compile_playbook_document(document)
        root = get_keprix_home() / "playbooks" / "promoted"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{compiled.graph_id}.yaml"
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        link = self.links.add(
            skill_slug=skill_slug,
            automation_type="playbook",
            automation_id=compiled.graph_id,
            edit_url=f"/playbooks/studio/{compiled.graph_id}",
            metadata={"path": str(path)},
        )
        return {"automation_type": "playbook", "id": compiled.graph_id, "edit_url": link.edit_url, "link": link.to_dict(), "artifact": document}

    def _promote_agent_app(self, skill_slug: str, *, name: str | None, schedule: str | None) -> dict[str, Any]:
        manifest = agent_app_manifest(skill_slug, name=name, schedule=schedule)
        app_root = get_keprix_home() / "agent-apps" / manifest["name"]
        app_root.mkdir(parents=True, exist_ok=True)
        (app_root / "agent.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        (app_root / "instructions.md").write_text(f"Use the `{skill_slug}` skill to complete the requested workflow.\n", encoding="utf-8")
        (app_root / "README.md").write_text(f"# {manifest['display_name']}\n\nSkill-backed Agent App for `{skill_slug}`.\n", encoding="utf-8")
        link = self.links.add(
            skill_slug=skill_slug,
            automation_type="agent_app",
            automation_id=manifest["name"],
            edit_url=f"/agent-apps/{manifest['name']}",
            metadata={"path": str(app_root), "schedule": schedule},
        )
        return {"automation_type": "agent_app", "id": manifest["name"], "edit_url": link.edit_url, "link": link.to_dict(), "artifact": manifest}
