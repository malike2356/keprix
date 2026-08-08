"""Navigation groups and items for the Keprix app shell.

Order follows natural operator workflows (accordion sidebar; one group open):
1. Daily work (chat, schedule, inbox)
2. Pipeline (people, CRM, outreach, discovery)
3. Knowledge (docs, files, memory)
4. Data and insights (RAG, analytics, models)
5. Research (deep research, model compare)
6. Apps and channels
7. Installed apps
8. Automations (agents, playbooks, schedules)
9. Security and trust
10. Billing
11. Admin (Developer last)
"""

from __future__ import annotations

from typing import Any

NAV_GROUP_LABELS: dict[str, str] = {
    "workspace": "Daily work",
    "pipeline": "Pipeline",
    "knowledge": "Knowledge",
    "data": "Data",
    "research": "Research",
    "apps": "Apps",
    "installed_apps": "Installed apps",
    "automations": "Automations",
    "security": "Security",
    "commerce": "Billing",
    "admin": "Admin",
}

NAV_GROUPS_ORDER: list[str] = [
    "workspace",
    "pipeline",
    "knowledge",
    "data",
    "research",
    "apps",
    "installed_apps",
    "automations",
    "security",
    "commerce",
    "admin",
]

# Curated nav. Admins/owners always get the full list.
# Users/operators get this minus admin group, minus items gated by off feature flags.
NAV_ITEMS: list[dict[str, Any]] = [
    # --- Daily work: start the day, talk, schedule, communicate ---
    {"id": "home", "label": "Home", "href": "/home", "group": "workspace", "icon": "home"},
    {"id": "chat", "label": "Chat", "href": "/chat", "group": "workspace", "icon": "chat"},
    {"id": "sessions", "label": "Sessions", "href": "/sessions", "group": "workspace", "icon": "chat"},
    {"id": "voice", "label": "Voice", "href": "/voice", "group": "workspace", "icon": "voice"},
    {"id": "tasks", "label": "Tasks", "href": "/tasks", "group": "workspace", "icon": "tasks"},
    {"id": "calendar", "label": "Calendar", "href": "/calendar", "group": "workspace", "icon": "calendar"},
    {"id": "vical", "label": "viCal", "href": "/vical", "group": "workspace", "icon": "calendar"},
    {"id": "notes", "label": "Notes", "href": "/notes", "group": "workspace", "icon": "notes"},
    {"id": "email", "label": "Email", "href": "/email", "group": "workspace", "icon": "email"},
    {"id": "notifications", "label": "Notifications", "href": "/notifications", "group": "workspace", "icon": "email"},
    # --- Pipeline: people, CRM, Soft Wall outreach, discovery ---
    {"id": "contacts", "label": "Contacts", "href": "/contacts", "group": "pipeline", "icon": "contacts"},
    {"id": "crm", "label": "CRM", "href": "/crm", "group": "pipeline", "icon": "contacts"},
    {"id": "crm-enrich", "label": "Sheet enrich", "href": "/crm/enrich", "group": "pipeline", "icon": "science"},
    {"id": "crm-discover", "label": "Discover", "href": "/crm/discover", "group": "pipeline", "icon": "search"},
    {"id": "crm-jobs", "label": "CRM jobs", "href": "/crm/jobs", "group": "pipeline", "icon": "monitoring"},
    {"id": "outreach", "label": "Outreach", "href": "/outreach", "group": "pipeline", "icon": "email"},
    {"id": "companies-house", "label": "Companies House", "href": "/companies-house", "group": "pipeline", "icon": "business"},
    {"id": "leads", "label": "Product signups", "href": "/leads", "group": "pipeline", "icon": "contacts"},
    {"id": "opportunities", "label": "Research opportunities", "href": "/opportunities", "group": "pipeline", "icon": "science"},
    {"id": "escalations", "label": "Escalations", "href": "/escalations", "group": "pipeline", "icon": "shield"},
    {"id": "worker-kb", "label": "Worker KB", "href": "/workers/kb", "group": "pipeline", "icon": "memory"},
    # --- Knowledge: documents, files, durable memory ---
    {"id": "documents", "label": "Documents", "href": "/documents", "group": "knowledge", "icon": "folder"},
    {"id": "document-agents", "label": "Document agents", "href": "/document-agents", "group": "knowledge", "icon": "folder"},
    {"id": "files", "label": "Files", "href": "/files", "group": "knowledge", "icon": "folder"},
    {"id": "gallery", "label": "Gallery", "href": "/gallery", "group": "knowledge", "icon": "image"},
    {"id": "memory", "label": "Memory", "href": "/memory", "group": "knowledge", "icon": "memory"},
    {"id": "memory-galaxy", "label": "Memory Galaxy", "href": "/memory/galaxy", "group": "knowledge", "icon": "memory"},
    {"id": "brain", "label": "Brain", "href": "/brain/graph", "group": "knowledge", "icon": "memory"},
    {"id": "tools", "label": "Tools", "href": "/admin/tools", "group": "knowledge", "icon": "tool"},
    {"id": "workspace-new", "label": "New workspace", "href": "/workspace/new", "group": "knowledge", "icon": "folder"},
    # --- Data: knowledge graph ops, pipelines, models, telemetry ---
    {"id": "brain-graph", "label": "Brain graph", "href": "/brain/graph", "group": "data", "icon": "memory"},
    {"id": "brain-health", "label": "Brain health", "href": "/brain/health", "group": "data", "icon": "monitoring"},
    {"id": "graphiti", "label": "Graphiti", "href": "/brain/graphiti", "group": "data", "icon": "memory"},
    {"id": "rag-pipeline", "label": "RAG Pipelines", "href": "/data?tab=rag", "group": "data", "icon": "science"},
    {"id": "playbook", "label": "Local models", "href": "/data?tab=models", "group": "data", "icon": "playbook"},
    {"id": "video-ingest", "label": "Video ingest", "href": "/data?tab=video", "group": "data", "icon": "video"},
    {"id": "aiva-analytics", "label": "Analytics", "href": "/analytics", "group": "data", "icon": "compare"},
    {"id": "analytics", "label": "Data analysis", "href": "/data?tab=analytics", "group": "data", "icon": "compare"},
    {"id": "usage", "label": "LLM usage", "href": "/data?tab=usage", "group": "data", "icon": "monitoring"},
    {"id": "observability", "label": "Observability", "href": "/data?tab=observability", "group": "data", "icon": "activity"},
    # --- Research: deep research and evaluation ---
    {"id": "research", "label": "Deep Research", "href": "/research", "group": "research", "icon": "science"},
    {"id": "compare", "label": "Compare Models", "href": "/compare", "group": "research", "icon": "compare"},
    # --- Apps: installable surfaces, channels, builders ---
    {"id": "hub", "label": "Hub", "href": "/hub", "group": "apps", "icon": "apps"},
    {"id": "agent-apps", "label": "Agent Apps", "href": "/agent-apps", "group": "apps", "icon": "apps"},
    {"id": "skills", "label": "Skills Hub", "href": "/skills", "group": "apps", "icon": "skills"},
    {"id": "domain-packs", "label": "Domain Packs", "href": "/domain-packs", "group": "apps", "icon": "skills"},
    {"id": "builder", "label": "Project Builder", "href": "/builder", "group": "apps", "icon": "code"},
    {"id": "design-preview", "label": "Design preview", "href": "/design/preview", "group": "apps", "icon": "image"},
    {"id": "channels", "label": "Channels", "href": "/dashboard/channels", "group": "apps", "icon": "extension"},
    {"id": "messaging-settings", "label": "Messaging", "href": "/settings/messaging", "group": "apps", "icon": "email"},
    {"id": "voice-wake", "label": "Wake words", "href": "/settings/voice/wake-words", "group": "apps", "icon": "settings"},
    {"id": "migrate", "label": "Migrate", "href": "/migrate", "group": "apps", "icon": "backup"},
    # --- Automations: orchestrate agents and schedules ---
    {"id": "control-center", "label": "Control Center", "href": "/control-center", "group": "automations", "icon": "hub"},
    {"id": "agent-os-glass", "label": "Agent OS", "href": "/agent-os/glass", "group": "automations", "icon": "dashboard"},
    {"id": "agent-studio", "label": "Agent Studio", "href": "/agent-studio", "group": "automations", "icon": "apps"},
    {"id": "agent-teams", "label": "Agent Teams", "href": "/admin/teams", "group": "automations", "icon": "extension"},
    {"id": "agent-runtime", "label": "Agent Runtime", "href": "/agent-runtime", "group": "automations", "icon": "extension"},
    {"id": "a2a", "label": "A2A", "href": "/a2a", "group": "automations", "icon": "hub"},
    {"id": "playbooks", "label": "Playbooks", "href": "/playbooks", "group": "automations", "icon": "playbook"},
    {"id": "playbook-triggers", "label": "Triggers", "href": "/playbooks/triggers", "group": "automations", "icon": "schedule"},
    {"id": "integrations", "label": "Integrations", "href": "/integrations", "group": "automations", "icon": "extension"},
    {"id": "sidecars", "label": "Sidecars", "href": "/settings/sidecars", "group": "automations", "icon": "extension"},
    {"id": "cron", "label": "Cron Jobs", "href": "/admin/cron", "group": "automations", "icon": "schedule"},
    {"id": "mcp", "label": "MCP Servers", "href": "/admin/mcp", "group": "automations", "icon": "extension"},
    {"id": "browser-adoption", "label": "Browser", "href": "/browser", "group": "automations", "icon": "extension"},
    {"id": "coding-adoption", "label": "Coding", "href": "/admin/coding", "group": "automations", "icon": "code"},
    {"id": "admin-code-agent", "label": "Code-agent", "href": "/admin/code-agent", "group": "automations", "icon": "code"},
    {"id": "ponytail-ladder", "label": "Ponytail ladder", "href": "/coding/ladder", "group": "automations", "icon": "code"},
    {"id": "tools-adoption", "label": "Tool library", "href": "/admin/tools", "group": "automations", "icon": "extension"},
    {"id": "evals", "label": "Evals", "href": "/evals", "group": "automations", "icon": "science"},
    {"id": "agent-os-improvements", "label": "Improvements", "href": "/agent-os/improvements", "group": "automations", "icon": "monitoring"},
    # --- Security: secrets, gates, support ---
    {"id": "vault", "label": "Vault", "href": "/vault", "group": "security", "icon": "lock"},
    {"id": "vault-setup", "label": "Vault setup", "href": "/vault/setup", "group": "security", "icon": "folder"},
    {"id": "knowledge-vault-settings", "label": "Knowledge vault", "href": "/settings/vault", "group": "security", "icon": "folder"},
    {"id": "review-gateway", "label": "Review gateway", "href": "/review-gateway", "group": "security", "icon": "shield"},
    {"id": "channel-shield", "label": "Channel Shield", "href": "/channel-shield", "group": "security", "icon": "shield"},
    {"id": "scout-warden", "label": "Scout Warden", "href": "/admin/scout-warden", "group": "security", "icon": "shield"},
    {"id": "scout-ops", "label": "Scout kill & sensors", "href": "/admin/scout-ops", "group": "security", "icon": "shield"},
    {"id": "dsar", "label": "DSAR", "href": "/admin/dsar", "group": "security", "icon": "shield"},
    {"id": "operator-copilot", "label": "Operator copilot", "href": "/control-center", "group": "security", "icon": "extension"},
    {"id": "support", "label": "Support", "href": "/support", "group": "security", "icon": "help"},
    # --- Billing ---
    {"id": "billing", "label": "Billing", "href": "/settings/billing", "group": "commerce", "icon": "payments"},
    {"id": "upgrade", "label": "Keprix upgrades", "href": "/settings/upgrade", "group": "commerce", "icon": "backup"},
    # --- Admin: overview -> people -> product -> governance -> reliability -> platform ---
    {"id": "settings", "label": "Settings", "href": "/settings", "group": "admin", "icon": "settings"},
    {"id": "dashboard", "label": "Dashboard", "href": "/dashboard", "group": "admin", "icon": "monitoring"},
    {"id": "admin", "label": "Admin", "href": "/dashboard", "group": "admin", "icon": "shield"},
    {"id": "users", "label": "Users", "href": "/settings/users", "group": "admin", "icon": "users"},
    {"id": "tenants", "label": "Tenants", "href": "/tenants", "group": "admin", "icon": "users"},
    {"id": "modules", "label": "Modules", "href": "/settings/modules", "group": "admin", "icon": "apps"},
    {"id": "feature-flags", "label": "Feature Flags", "href": "/admin/feature-flags", "group": "admin", "icon": "apps"},
    {"id": "admin-quotas", "label": "Quotas", "href": "/admin/quotas", "group": "admin", "icon": "monitoring"},
    {"id": "admin-tool-acl", "label": "Tool ACL", "href": "/admin/tool-acl", "group": "admin", "icon": "shield"},
    {"id": "admin-fleet", "label": "Fleet", "href": "/admin/fleet", "group": "admin", "icon": "monitoring"},
    {"id": "admin-companion", "label": "Companion", "href": "/admin/companion", "group": "admin", "icon": "users"},
    {"id": "admin-code-agent-ops", "label": "Code-agent sessions", "href": "/admin/code-agent", "group": "admin", "icon": "code"},
    {"id": "admin-typed-agents", "label": "Typed agents", "href": "/admin/typed-agents", "group": "admin", "icon": "apps"},
    {"id": "admin-kernel", "label": "Kernel", "href": "/admin/kernel", "group": "admin", "icon": "apps"},
    {"id": "admin-interfaces", "label": "Interfaces", "href": "/admin/interfaces", "group": "admin", "icon": "apps"},
    {"id": "admin-intent", "label": "Intent schemas", "href": "/admin/intent", "group": "admin", "icon": "apps"},
    {"id": "admin-tool-adapters", "label": "Tool adapters", "href": "/admin/tool-adapters", "group": "admin", "icon": "apps"},
    {"id": "admin-personas", "label": "Personas", "href": "/admin/personas", "group": "admin", "icon": "users"},
    {"id": "admin-workspace-ops", "label": "Workspace ops", "href": "/admin/workspace-ops", "group": "admin", "icon": "settings"},
    {"id": "admin-network-egress", "label": "Network egress", "href": "/admin/network-egress", "group": "admin", "icon": "shield"},
    {"id": "admin-isolation-audit", "label": "Isolation audit", "href": "/admin/isolation-audit", "group": "admin", "icon": "shield"},
    {"id": "admin-upstream", "label": "Hermes upstream", "href": "/admin/upstream", "group": "admin", "icon": "monitoring"},
    {"id": "backup", "label": "Backup", "href": "/admin/backup", "group": "admin", "icon": "backup"},
    {"id": "readiness", "label": "Readiness", "href": "/admin/readiness", "group": "admin", "icon": "monitoring"},
    {"id": "self-knowledge", "label": "Self-Knowledge", "href": "/admin/self-knowledge", "group": "admin", "icon": "apps"},
    {"id": "module-inventory", "label": "Module inventory", "href": "/developer/module-inventory", "group": "admin", "icon": "monitoring"},
    {"id": "developer", "label": "Developer", "href": "/developer", "group": "admin", "icon": "code"},
]

# When a flag is off, hide these nav ids for non-admin roles.
# Flags are progressive UX switches, not a full inventory of every backend package.
FLAG_NAV_GATES: dict[str, set[str]] = {
    "voice_input": {"voice", "voice-wake"},
    "data_workspace": {"rag-pipeline", "analytics", "aiva-analytics", "video-ingest", "observability"},
    "opportunity_engine": {"opportunities", "contacts"},
    "playbooks": {"playbooks", "playbook-triggers"},
    "research": {"research", "compare"},
    "calendar": {"calendar", "vical"},
    "email": {"email", "messaging-settings"},
    "contacts": {"contacts"},
    "crm_funnel": {"crm", "crm-enrich", "crm-discover", "crm-jobs", "outreach", "companies-house"},
    "agent_apps": {"agent-apps", "hub"},
    "builder": {"builder"},
    "browser": {"browser-adoption"},
    "evals": {"evals"},
    "coding": {"coding-adoption", "ponytail-ladder"},
    "governance": {"review-gateway", "operator-copilot"},
    "channel_shield": {"channel-shield"},
    "commerce": {"billing", "upgrade"},
}

ADMIN_ROLES = frozenset({"admin", "owner"})

ROLE_HIDDEN_GROUPS: dict[str, set[str]] = {
    "viewer": {"admin", "commerce", "automations"},
    "user": {"admin"},
    "operator": {"admin"},
    "admin": set(),
    "owner": set(),
}


def _filter_by_feature_flags(
    items: list[dict[str, Any]],
    feature_flags: dict[str, bool] | None,
) -> list[dict[str, Any]]:
    if not feature_flags:
        return items
    hidden_ids: set[str] = set()
    for flag_id, nav_ids in FLAG_NAV_GATES.items():
        if feature_flags.get(flag_id, True) is False:
            hidden_ids.update(nav_ids)
    if not hidden_ids:
        return items
    return [item for item in items if item["id"] not in hidden_ids]


def navigation_for_role(
    role: str,
    *,
    feature_flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build sidebar navigation for a role.

    Admin/owner: full curated nav (no simplified-mode strip, no flag gates).
    User/operator: work surface only; feature flags can reveal more modules.
    """
    is_admin = role in ADMIN_ROLES
    hidden = ROLE_HIDDEN_GROUPS.get(role, ROLE_HIDDEN_GROUPS["viewer"])
    visible_groups = [group for group in NAV_GROUPS_ORDER if group not in hidden]
    items = [item for item in NAV_ITEMS if item["group"] not in hidden]

    if not is_admin:
        try:
            from keprix.agent_os.workflow_audit_service import agent_os_enabled

            if not agent_os_enabled():
                items = [item for item in items if not str(item["id"]).startswith("agent-os-")]
        except Exception:
            items = [item for item in items if not str(item["id"]).startswith("agent-os-")]
        try:
            from keprix.agent_os.simplified_mode import filter_navigation

            items = filter_navigation(items)
        except Exception:
            pass
        items = _filter_by_feature_flags(items, feature_flags)

    # Drop empty groups so the accordion only shows groups with items.
    present = {str(item["group"]) for item in items}
    visible_groups = [group for group in visible_groups if group in present or group == "installed_apps"]

    return {
        "groups": [{"id": group, "label": NAV_GROUP_LABELS[group]} for group in visible_groups],
        "items": items,
    }
