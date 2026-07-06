"""Navigation groups and items for the Keprix app shell."""

from __future__ import annotations

from typing import Any

NAV_GROUP_LABELS: dict[str, str] = {
    "workspace": "Workspace",
    "apps": "Apps",
    "data": "Data",
    "research": "Research",
    "automations": "Automations",
    "commerce": "Commerce",
    "security": "Security",
    "admin": "Admin",
}

NAV_GROUPS_ORDER: list[str] = [
    "workspace",
    "apps",
    "data",
    "research",
    "automations",
    "commerce",
    "security",
    "admin",
]

NAV_ITEMS: list[dict[str, Any]] = [
    {"id": "launcher", "label": "Launcher", "href": "/launcher", "group": "workspace", "icon": "hub"},
    {"id": "chat", "label": "Chat", "href": "/chat", "group": "workspace", "icon": "chat"},
    {"id": "documents", "label": "Documents", "href": "/documents", "group": "workspace", "icon": "folder"},
    {"id": "notes", "label": "Notes", "href": "/notes", "group": "workspace", "icon": "notes"},
    {"id": "tasks", "label": "Tasks", "href": "/tasks", "group": "workspace", "icon": "tasks"},
    {"id": "calendar", "label": "Calendar", "href": "/calendar", "group": "workspace", "icon": "calendar"},
    {"id": "email", "label": "Email", "href": "/email", "group": "workspace", "icon": "email"},
    {"id": "notifications", "label": "Notifications", "href": "/notifications", "group": "workspace", "icon": "email"},
    {"id": "contacts", "label": "Contacts", "href": "/contacts", "group": "workspace", "icon": "contacts"},
    {"id": "gallery", "label": "Gallery", "href": "/gallery", "group": "workspace", "icon": "image"},
    {"id": "memory", "label": "Memory", "href": "/memory", "group": "workspace", "icon": "memory"},
    {"id": "opportunities", "label": "Opportunities", "href": "/opportunities", "group": "research", "icon": "science"},
    {"id": "research", "label": "Deep Research", "href": "/research", "group": "research", "icon": "science"},
    {"id": "compare", "label": "Compare Models", "href": "/compare", "group": "research", "icon": "compare"},
    {"id": "playbook", "label": "Local models", "href": "/playbook", "group": "data", "icon": "playbook"},
    {"id": "rag-pipeline", "label": "RAG Pipelines", "href": "/rag-pipeline", "group": "data", "icon": "science"},
    {"id": "analytics", "label": "Analytics workspace", "href": "/analytics", "group": "data", "icon": "compare"},
    {"id": "usage", "label": "LLM usage", "href": "/usage", "group": "data", "icon": "monitoring"},
    {"id": "playbooks", "label": "Playbooks", "href": "/playbooks", "group": "automations", "icon": "playbook"},
    {"id": "agent-teams", "label": "Agent Teams", "href": "/admin/teams", "group": "automations", "icon": "extension"},
    {"id": "browser-adoption", "label": "Browser", "href": "/browser", "group": "automations", "icon": "extension"},
    {"id": "analytics-adoption", "label": "Analytics", "href": "/analytics", "group": "automations", "icon": "compare"},
    {"id": "coding-adoption", "label": "Coding", "href": "/admin/coding", "group": "automations", "icon": "code"},
    {"id": "tools-adoption", "label": "Tools", "href": "/admin/tools", "group": "automations", "icon": "extension"},
    {"id": "evals", "label": "Evals", "href": "/evals", "group": "automations", "icon": "science"},
    {"id": "control-center", "label": "Control Center", "href": "/control-center", "group": "automations", "icon": "hub"},
    {"id": "agent-studio", "label": "Agent Studio", "href": "/agent-studio", "group": "automations", "icon": "apps"},
    {"id": "agent-apps", "label": "Agent Apps", "href": "/agent-apps", "group": "automations", "icon": "apps"},
    {"id": "vault", "label": "Vault", "href": "/vault", "group": "security", "icon": "lock"},
    {"id": "cron", "label": "Cron Jobs", "href": "/admin/cron", "group": "automations", "icon": "schedule"},
    {"id": "mcp", "label": "MCP Servers", "href": "/admin/mcp", "group": "automations", "icon": "extension"},
    {"id": "backup", "label": "Backup", "href": "/admin/backup", "group": "admin", "icon": "backup"},
    {"id": "users", "label": "Users", "href": "/settings/users", "group": "admin", "icon": "users"},
    {"id": "billing", "label": "Billing", "href": "/settings/billing", "group": "admin", "icon": "payments"},
    {"id": "settings", "label": "Settings", "href": "/settings", "group": "admin", "icon": "settings"},
    {"id": "developer", "label": "Developer", "href": "/developer", "group": "admin", "icon": "code"},
    {"id": "skills", "label": "Skills Hub", "href": "/skills", "group": "apps", "icon": "skills"},
]

ROLE_HIDDEN_GROUPS: dict[str, set[str]] = {
    "viewer": {"admin", "commerce"},
    "user": set(),
    "admin": set(),
    "owner": set(),
}


def navigation_for_role(role: str) -> dict[str, Any]:
    hidden = ROLE_HIDDEN_GROUPS.get(role, ROLE_HIDDEN_GROUPS["viewer"])
    visible_groups = [group for group in NAV_GROUPS_ORDER if group not in hidden]
    items = [item for item in NAV_ITEMS if item["group"] not in hidden]
    return {
        "groups": [{"id": group, "label": NAV_GROUP_LABELS[group]} for group in visible_groups],
        "items": items,
    }
