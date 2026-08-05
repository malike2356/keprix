"""Workspace folder template presets for Agent OS memory maps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from keprix.workspace.index_generator import WorkspaceIndexer
from keprix.workspace.keprix_md_generator import render_keprix_md
from keprix_constants import get_keprix_home


@dataclass(frozen=True)
class WorkspaceTemplate:
    id: str
    name: str
    folders: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "folders": list(self.folders),
            "description": self.description,
        }


TEMPLATES: dict[str, WorkspaceTemplate] = {
    "knowledge_pipeline": WorkspaceTemplate(
        id="knowledge_pipeline",
        name="Knowledge Pipeline",
        folders=("context", "raw", "wiki", "outputs"),
        description="Research inputs, structured knowledge, and deliverables.",
    ),
    "property_investor": WorkspaceTemplate(
        id="property_investor",
        name="Property Investor",
        folders=("deals", "tenants", "compliance", "reports"),
        description="Property deal analysis and operations workspace.",
    ),
    "developer": WorkspaceTemplate(
        id="developer",
        name="Developer",
        folders=("specs", "architecture", "releases", "reviews"),
        description="Software planning, architecture, releases, and review notes.",
    ),
    "client_delivery": WorkspaceTemplate(
        id="client_delivery",
        name="Client Delivery",
        folders=("context", "clients", "deliverables", "feedback"),
        description="Agency or consultant client delivery workspace.",
    ),
    "executive_assistant": WorkspaceTemplate(
        id="executive_assistant",
        name="Executive Assistant",
        folders=("context", "raw", "wiki", "outputs"),
        description="Personal operating context, hot knowledge, and outputs.",
    ),
    "blank": WorkspaceTemplate(
        id="blank",
        name="Blank",
        folders=(),
        description="Start with an empty workspace root.",
    ),
}


def list_templates() -> list[WorkspaceTemplate]:
    return list(TEMPLATES.values())


def get_template(template_id: str) -> WorkspaceTemplate:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"Unknown workspace template: {template_id}") from exc


def workspace_root(name: str) -> Path:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name.strip()).strip("-") or "workspace"
    return get_keprix_home() / "workspaces" / slug


def create_workspace(name: str, template_id: str = "knowledge_pipeline") -> dict[str, object]:
    template = get_template(template_id)
    root = workspace_root(name)
    root.mkdir(parents=True, exist_ok=True)
    for folder in template.folders:
        (root / folder).mkdir(parents=True, exist_ok=True)
    if "context" in template.folders:
        (root / "wiki" / "hot.md").parent.mkdir(parents=True, exist_ok=True)
        if "wiki" in template.folders:
            (root / "wiki" / "hot.md").touch(exist_ok=True)
            (root / "wiki" / "index.md").touch(exist_ok=True)
            (root / "wiki" / "log.md").touch(exist_ok=True)
            if template.id == "executive_assistant":
                from keprix.workspace.hot_cache_config import HotCacheConfig, save_hot_cache_config

                save_hot_cache_config(root, HotCacheConfig(enabled=True))
        for filename in (
            "about-business.md",
            "about-me.md",
            "priorities.md",
            "writing-samples.md",
            "guardrails.md",
            "cadence-preferences.md",
            "intake.json",
        ):
            (root / "context" / filename).parent.mkdir(parents=True, exist_ok=True)
            (root / "context" / filename).touch(exist_ok=True)
    indexer = WorkspaceIndexer(root)
    indexer.reindex_all()
    guide = render_keprix_md(root, template)
    (root / "KEPRIX.md").write_text(guide, encoding="utf-8")
    (root / "CLAUDE.md").write_text(guide, encoding="utf-8")
    return {"id": root.name, "name": name, "path": str(root), "template": template.to_dict()}
