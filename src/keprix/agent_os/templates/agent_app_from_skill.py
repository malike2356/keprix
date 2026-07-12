"""Agent App promotion template."""

from __future__ import annotations

from typing import Any


def agent_app_manifest(skill_slug: str, *, name: str | None = None, schedule: str | None = None) -> dict[str, Any]:
    app_name = (name or skill_slug).replace("_", "-").replace(" ", "-").lower()
    manifest: dict[str, Any] = {
        "name": app_name,
        "version": "0.1.0",
        "display_name": name or skill_slug.replace("-", " ").title(),
        "description": f"Agent App runner for the {skill_slug} skill.",
        "category": "custom",
        "runtime": "agent",
        "tools": [],
        "inputs": [{"id": "input", "label": "Input", "type": "textarea", "required": False}],
        "outputs": [{"id": "markdown", "type": "markdown"}],
        "metadata": {"skill": skill_slug, "runner": "skill"},
    }
    if schedule:
        manifest["schedule"] = {"suggested": schedule, "timezone": "user"}
    return manifest
