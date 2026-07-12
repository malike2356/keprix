import type { UiContract, UiNavItem } from "@/lib/ui-contract";

export type NavGroupId =
  | "workspace"
  | "apps"
  | "installed_apps"
  | "data"
  | "research"
  | "automations"
  | "commerce"
  | "security"
  | "admin";

export type NavItem = {
  id: string;
  label: string;
  href: string;
  icon: string;
  description?: string;
  group: NavGroupId;
};

export const navGroupLabels: Record<NavGroupId, string> = {
  workspace: "Workspace",
  apps: "Apps",
  installed_apps: "Installed apps",
  data: "Data",
  research: "Research",
  automations: "Automations",
  commerce: "Commerce",
  security: "Security",
  admin: "Admin",
};

export const navGroupsOrder: NavGroupId[] = [
  "workspace",
  "apps",
  "installed_apps",
  "data",
  "research",
  "automations",
  "commerce",
  "security",
  "admin",
];

/** Static fallback aligned with backend ui_contract.navigation.NAV_ITEMS */
export const primaryNavigation: NavItem[] = [
  { id: "home", label: "Home", href: "/home", icon: "home", group: "workspace" },
  { id: "sessions", label: "Sessions", href: "/sessions", icon: "chat", group: "workspace" },
  { id: "brain", label: "Brain", href: "/brain/graph", icon: "memory", group: "workspace" },
  { id: "skills", label: "Skills", href: "/skills", icon: "skills", group: "workspace" },
  { id: "tasks", label: "Tasks", href: "/tasks", icon: "tasks", group: "workspace" },
  { id: "tools", label: "Tools", href: "/admin/tools", icon: "tool", group: "workspace" },
  { id: "voice", label: "Voice", href: "/voice", icon: "voice", group: "workspace" },
  { id: "settings", label: "Settings", href: "/settings", icon: "settings", group: "admin" },
  { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: "monitoring", group: "admin" },
  { id: "admin", label: "Admin", href: "/dashboard", icon: "shield", group: "admin" },
  { id: "brain-graph", label: "Brain graph", href: "/brain/graph", icon: "memory", group: "data" },
  { id: "brain-health", label: "Brain health", href: "/brain/health", icon: "monitoring", group: "data" },
  { id: "graphiti", label: "Graphiti", href: "/brain/graphiti", icon: "memory", group: "data" },
  { id: "documents", label: "Documents", href: "/documents", icon: "folder", group: "data" },
  { id: "notes", label: "Notes", href: "/notes", icon: "notes", group: "data" },
  { id: "memory", label: "Memory", href: "/memory", icon: "memory", group: "data" },
  { id: "memory-galaxy", label: "Memory Galaxy", href: "/memory/galaxy", icon: "memory", group: "workspace" },
  { id: "hub", label: "Hub", href: "/hub", icon: "apps", group: "apps" },
  { id: "agent-apps", label: "Agent Apps", href: "/agent-apps", icon: "apps", group: "apps" },
  { id: "builder", label: "Project Builder", href: "/builder", icon: "code", group: "apps" },
  { id: "design-preview", label: "Design preview", href: "/design/preview", icon: "image", group: "apps" },
  { id: "domain-packs", label: "Domain Packs", href: "/domain-packs", icon: "skills", group: "apps" },
  { id: "migrate", label: "Migrate", href: "/migrate", icon: "backup", group: "apps" },
  { id: "channels", label: "Channels", href: "/dashboard/channels", icon: "extension", group: "apps" },
  { id: "messaging-settings", label: "Messaging", href: "/settings/messaging", icon: "email", group: "apps" },
  { id: "voice-wake", label: "Wake words", href: "/settings/voice/wake-words", icon: "settings", group: "apps" },
  { id: "opportunities", label: "Opportunities", href: "/opportunities", icon: "science", group: "research" },
  { id: "research", label: "Deep Research", href: "/research", icon: "science", group: "research" },
  { id: "compare", label: "Compare Models", href: "/compare", icon: "compare", group: "research" },
  { id: "playbook", label: "Local models", href: "/playbook", icon: "playbook", group: "data" },
  { id: "agent-os-glass", label: "Agent OS", href: "/agent-os/glass", icon: "dashboard", group: "automations" },
  { id: "playbooks", label: "Playbooks", href: "/playbooks", icon: "playbook", group: "automations" },
  { id: "integrations", label: "Integrations", href: "/integrations", icon: "extension", group: "automations" },
  { id: "agent-teams", label: "Agent Teams", href: "/admin/teams", icon: "extension", group: "automations" },
  { id: "agent-runtime", label: "Agent Runtime", href: "/agent-runtime", icon: "extension", group: "automations" },
  { id: "a2a", label: "A2A", href: "/a2a", icon: "hub", group: "automations" },
  { id: "browser-adoption", label: "Browser", href: "/browser", icon: "extension", group: "automations" },
  { id: "analytics-adoption", label: "Analytics", href: "/analytics", icon: "compare", group: "automations" },
  { id: "coding-adoption", label: "Coding", href: "/admin/coding", icon: "code", group: "automations" },
  { id: "ponytail-ladder", label: "Ponytail ladder", href: "/coding/ladder", icon: "code", group: "automations" },
  { id: "tools-adoption", label: "Tools", href: "/admin/tools", icon: "extension", group: "automations" },
  { id: "evals", label: "Evals", href: "/evals", icon: "science", group: "automations" },
  { id: "control-center", label: "Control Center", href: "/control-center", icon: "hub", group: "automations" },
  { id: "agent-studio", label: "Agent Studio", href: "/agent-studio", icon: "apps", group: "automations" },
  { id: "rag-pipeline", label: "RAG Pipelines", href: "/rag-pipeline", icon: "science", group: "data" },
  { id: "analytics", label: "Analytics", href: "/analytics", icon: "compare", group: "data" },
  { id: "usage", label: "LLM usage", href: "/usage", icon: "monitoring", group: "data" },
  { id: "observability", label: "Observability", href: "/observability", icon: "monitoring", group: "data" },
  { id: "video-ingest", label: "Video ingest", href: "/ingest/video", icon: "image", group: "data" },
  { id: "review-gateway", label: "Review gateway", href: "/review-gateway", icon: "shield", group: "security" },
  { id: "vault", label: "Vault", href: "/vault", icon: "lock", group: "security" },
  { id: "vault-setup", label: "Vault setup", href: "/vault/setup", icon: "folder", group: "security" },
  { id: "knowledge-vault-settings", label: "Knowledge vault", href: "/settings/vault", icon: "folder", group: "security" },
  { id: "support", label: "Support", href: "/support", icon: "help", group: "security" },
  { id: "operator-copilot", label: "Operator copilot", href: "/control-center", icon: "extension", group: "security" },
  { id: "cron", label: "Cron Jobs", href: "/admin/cron", icon: "schedule", group: "automations" },
  { id: "mcp", label: "MCP Servers", href: "/admin/mcp", icon: "extension", group: "automations" },
  { id: "backup", label: "Backup", href: "/admin/backup", icon: "backup", group: "admin" },
  { id: "users", label: "Users", href: "/settings/users", icon: "users", group: "admin" },
  { id: "billing", label: "Billing", href: "/settings/billing", icon: "payments", group: "admin" },
  { id: "upgrade", label: "Keprix upgrades", href: "/settings/upgrade", icon: "backup", group: "admin" },
  { id: "modules", label: "Modules", href: "/settings/modules", icon: "apps", group: "admin" },
  { id: "admin-quotas", label: "Quotas", href: "/admin/quotas", icon: "monitoring", group: "admin" },
  { id: "admin-tool-acl", label: "Tool ACL", href: "/admin/tools", icon: "shield", group: "admin" },
  { id: "admin-network-egress", label: "Network egress", href: "/admin/network-egress", icon: "shield", group: "admin" },
  { id: "admin-isolation-audit", label: "Isolation audit", href: "/admin/isolation-audit", icon: "shield", group: "admin" },
  { id: "developer", label: "Developer", href: "/developer", icon: "code", group: "admin" },
  { id: "module-inventory", label: "Module inventory", href: "/developer/module-inventory", icon: "monitoring", group: "admin" },
];

export const mobilePrimaryNavigation: NavItem[] = primaryNavigation.filter((item) =>
  ["home", "sessions", "brain", "tasks", "settings"].includes(item.id),
);

export type LauncherCard = {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: string;
};

export const launcherCards: LauncherCard[] = [
  { id: "chat", title: "Chat", description: "Talk to your local agent with tool access.", href: "/chat", icon: "chat" },
  { id: "research", title: "Deep Research", description: "Run cited research with depth controls.", href: "/research", icon: "science" },
  { id: "documents", title: "Documents", description: "Browse workspace files and uploads.", href: "/documents", icon: "folder" },
  { id: "notes", title: "Notes", description: "Capture linked notes and references.", href: "/notes", icon: "notes" },
  { id: "tasks", title: "Tasks", description: "Track work items and follow-ups.", href: "/tasks", icon: "tasks" },
  { id: "calendar", title: "Calendar", description: "Review schedules and deadlines.", href: "/calendar", icon: "calendar" },
  { id: "email", title: "Email", description: "Triage inbox threads with AI summaries.", href: "/email", icon: "email" },
  { id: "contacts", title: "Contacts", description: "Search people and sync address books.", href: "/contacts", icon: "contacts" },
  { id: "playbook", title: "Playbook", description: "Scan hardware and manage local models.", href: "/playbook", icon: "playbook" },
  { id: "analytics", title: "Analytics", description: "Run verified Python analytics in an isolated session.", href: "/analytics", icon: "compare" },
  { id: "compare", title: "Compare Models", description: "Blind A/B model evaluation.", href: "/compare", icon: "compare" },
  { id: "usage", title: "LLM usage", description: "Monitor token consumption and estimated spend.", href: "/usage", icon: "monitoring" },
  { id: "video-ingest", title: "Video ingest", description: "Create transcript and frame manifests from local or remote videos.", href: "/ingest/video", icon: "image" },
  { id: "design-preview", title: "Design preview", description: "Inspect local HTML artifacts and copy component context.", href: "/design/preview", icon: "image" },
  { id: "graphiti", title: "Graphiti bridge", description: "Ingest reports and notes into a graph memory MCP.", href: "/brain/graphiti", icon: "memory" },
  { id: "gallery", title: "Gallery", description: "Review generated and uploaded images.", href: "/gallery", icon: "image" },
  { id: "vault", title: "Vault", description: "Manage encrypted credentials.", href: "/vault", icon: "lock" },
  { id: "cron", title: "Cron Jobs", description: "Schedule recurring agent tasks.", href: "/admin/cron", icon: "schedule" },
  { id: "mcp", title: "MCP Servers", description: "Connect external tool servers.", href: "/admin/mcp", icon: "extension" },
  { id: "agent-apps", title: "Agent Apps", description: "Install ready-made workflows or ship your own apps.", href: "/agent-apps", icon: "apps" },
  { id: "agent-os-glass", title: "Agent OS", description: "Glass dashboard: agents, memory, tasks, tokens, ship defaults.", href: "/agent-os/glass", icon: "dashboard" },
  { id: "agent-os-onboarding", title: "Agent OS onboarding", description: "Day 1 / 7 / 30 milestones and activation checklist.", href: "/agent-os/onboarding", icon: "monitoring" },
  { id: "skills", title: "Skills Hub", description: "Browse installed skills and packs.", href: "/skills", icon: "skills" },
  { id: "agent-teams", title: "Agent Teams", description: "YAML agent crews and multi-agent workflows (not human users).", href: "/admin/teams", icon: "extension" },
  { id: "settings", title: "Settings", description: "Configure providers, channels, and identity.", href: "/settings", icon: "settings" },
];

export function navigationFromContract(contract: UiContract | null): {
  groups: Array<{ id: NavGroupId; label: string }>;
  items: NavItem[];
} {
  if (!contract?.navigation) {
    return {
      groups: navGroupsOrder
        .map((id) => ({ id, label: navGroupLabels[id] }))
        .filter((group) => primaryNavigation.some((item) => item.group === group.id)),
      items: primaryNavigation,
    };
  }

  const groupIds = contract.navigation.groups.map((group) => group.id as NavGroupId);
  const items: NavItem[] = contract.navigation.items.map((item: UiNavItem) => ({
    id: item.id,
    label: item.label,
    href: item.href,
    icon: item.icon,
    group: item.group as NavGroupId,
  }));
  const installedAppItems: NavItem[] = (contract.installed_apps ?? []).map((app) => ({
    id: `built-app-${app.id}`,
    label: app.label,
    href: app.entry,
    icon: app.icon || "apps",
    group: "installed_apps",
  }));

  return {
    groups: groupIds.map((id) => ({
      id,
      label: contract.navigation.groups.find((group) => group.id === id)?.label || navGroupLabels[id],
    })),
    items: [...items, ...installedAppItems],
  };
}
