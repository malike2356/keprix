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
  data: "Data",
  research: "Research",
  apps: "Apps",
  installed_apps: "Installed apps",
  automations: "Automations",
  security: "Security",
  commerce: "Commerce",
  admin: "Admin",
};

export const navGroupsOrder: NavGroupId[] = [
  "workspace",
  "data",
  "research",
  "apps",
  "installed_apps",
  "automations",
  "security",
  "commerce",
  "admin",
];

/** Static fallback aligned with backend ui_contract.navigation.NAV_ITEMS */
export const primaryNavigation: NavItem[] = [
  // Workspace
  { id: "home", label: "Home", href: "/home", icon: "home", group: "workspace" },
  { id: "chat", label: "Chat", href: "/chat", icon: "chat", group: "workspace" },
  { id: "sessions", label: "Sessions", href: "/sessions", icon: "chat", group: "workspace" },
  { id: "voice", label: "Voice", href: "/voice", icon: "voice", group: "workspace" },
  { id: "tasks", label: "Tasks", href: "/tasks", icon: "tasks", group: "workspace" },
  { id: "calendar", label: "Calendar", href: "/calendar", icon: "calendar", group: "workspace" },
  { id: "vical", label: "viCal", href: "/vical", icon: "calendar", group: "workspace" },
  { id: "notes", label: "Notes", href: "/notes", icon: "notes", group: "workspace" },
  { id: "email", label: "Email", href: "/email", icon: "email", group: "workspace" },
  { id: "notifications", label: "Notifications", href: "/notifications", icon: "email", group: "workspace" },
  { id: "contacts", label: "Contacts", href: "/contacts", icon: "contacts", group: "workspace" },
  { id: "leads", label: "Leads", href: "/leads", icon: "contacts", group: "workspace" },
  { id: "documents", label: "Documents", href: "/documents", icon: "folder", group: "workspace" },
  { id: "files", label: "Files", href: "/files", icon: "folder", group: "workspace" },
  { id: "gallery", label: "Gallery", href: "/gallery", icon: "image", group: "workspace" },
  { id: "memory", label: "Memory", href: "/memory", icon: "memory", group: "workspace" },
  { id: "memory-galaxy", label: "Memory Galaxy", href: "/memory/galaxy", icon: "memory", group: "workspace" },
  { id: "brain", label: "Brain", href: "/brain/graph", icon: "memory", group: "workspace" },
  { id: "tools", label: "Tools", href: "/admin/tools", icon: "tool", group: "workspace" },
  { id: "workspace-new", label: "New workspace", href: "/workspace/new", icon: "folder", group: "workspace" },
  // Data
  { id: "brain-graph", label: "Brain graph", href: "/brain/graph", icon: "memory", group: "data" },
  { id: "brain-health", label: "Brain health", href: "/brain/health", icon: "monitoring", group: "data" },
  { id: "graphiti", label: "Graphiti", href: "/brain/graphiti", icon: "memory", group: "data" },
  { id: "rag-pipeline", label: "RAG Pipelines", href: "/data?tab=rag", icon: "science", group: "data" },
  { id: "playbook", label: "Local models", href: "/data?tab=models", icon: "playbook", group: "data" },
  { id: "video-ingest", label: "Video ingest", href: "/data?tab=video", icon: "video", group: "data" },
  { id: "analytics", label: "Analytics workspace", href: "/data?tab=analytics", icon: "compare", group: "data" },
  { id: "usage", label: "LLM usage", href: "/data?tab=usage", icon: "monitoring", group: "data" },
  { id: "observability", label: "Observability", href: "/data?tab=observability", icon: "activity", group: "data" },
  // Research
  { id: "research", label: "Deep Research", href: "/research", icon: "science", group: "research" },
  { id: "companies-house", label: "Companies House", href: "/companies-house", icon: "business", group: "research" },
  { id: "opportunities", label: "Opportunities", href: "/opportunities", icon: "science", group: "research" },
  { id: "compare", label: "Compare Models", href: "/compare", icon: "compare", group: "research" },
  // Apps
  { id: "hub", label: "Hub", href: "/hub", icon: "apps", group: "apps" },
  { id: "agent-apps", label: "Agent Apps", href: "/agent-apps", icon: "apps", group: "apps" },
  { id: "skills", label: "Skills Hub", href: "/skills", icon: "skills", group: "apps" },
  { id: "domain-packs", label: "Domain Packs", href: "/domain-packs", icon: "skills", group: "apps" },
  { id: "builder", label: "Project Builder", href: "/builder", icon: "code", group: "apps" },
  { id: "design-preview", label: "Design preview", href: "/design/preview", icon: "image", group: "apps" },
  { id: "channels", label: "Channels", href: "/dashboard/channels", icon: "extension", group: "apps" },
  { id: "messaging-settings", label: "Messaging", href: "/settings/messaging", icon: "email", group: "apps" },
  { id: "voice-wake", label: "Wake words", href: "/settings/voice/wake-words", icon: "settings", group: "apps" },
  { id: "migrate", label: "Migrate", href: "/migrate", icon: "backup", group: "apps" },
  // Automations
  { id: "control-center", label: "Control Center", href: "/control-center", icon: "hub", group: "automations" },
  { id: "agent-os-glass", label: "Agent OS", href: "/agent-os/glass", icon: "dashboard", group: "automations" },
  { id: "agent-studio", label: "Agent Studio", href: "/agent-studio", icon: "apps", group: "automations" },
  { id: "agent-teams", label: "Agent Teams", href: "/admin/teams", icon: "extension", group: "automations" },
  { id: "agent-runtime", label: "Agent Runtime", href: "/agent-runtime", icon: "extension", group: "automations" },
  { id: "a2a", label: "A2A", href: "/a2a", icon: "hub", group: "automations" },
  { id: "playbooks", label: "Playbooks", href: "/playbooks", icon: "playbook", group: "automations" },
  { id: "playbook-triggers", label: "Triggers", href: "/playbooks/triggers", icon: "schedule", group: "automations" },
  { id: "integrations", label: "Integrations", href: "/integrations", icon: "extension", group: "automations" },
  { id: "cron", label: "Cron Jobs", href: "/admin/cron", icon: "schedule", group: "automations" },
  { id: "mcp", label: "MCP Servers", href: "/admin/mcp", icon: "extension", group: "automations" },
  { id: "browser-adoption", label: "Browser", href: "/browser", icon: "extension", group: "automations" },
  { id: "coding-adoption", label: "Coding", href: "/admin/coding", icon: "code", group: "automations" },
  { id: "ponytail-ladder", label: "Ponytail ladder", href: "/coding/ladder", icon: "code", group: "automations" },
  { id: "tools-adoption", label: "Tool library", href: "/admin/tools", icon: "extension", group: "automations" },
  { id: "analytics-adoption", label: "Analytics", href: "/data?tab=analytics", icon: "compare", group: "automations" },
  { id: "evals", label: "Evals", href: "/evals", icon: "science", group: "automations" },
  // Security
  { id: "vault", label: "Vault", href: "/vault", icon: "lock", group: "security" },
  { id: "vault-setup", label: "Vault setup", href: "/vault/setup", icon: "folder", group: "security" },
  { id: "knowledge-vault-settings", label: "Knowledge vault", href: "/settings/vault", icon: "folder", group: "security" },
  { id: "review-gateway", label: "Review gateway", href: "/review-gateway", icon: "shield", group: "security" },
  { id: "channel-shield", label: "Channel Shield", href: "/channel-shield", icon: "shield", group: "security" },
  { id: "scout-warden", label: "Scout Warden", href: "/admin/scout-warden", icon: "shield", group: "security" },
  { id: "dsar", label: "DSAR", href: "/admin/dsar", icon: "shield", group: "security" },
  { id: "operator-copilot", label: "Operator copilot", href: "/control-center", icon: "extension", group: "security" },
  { id: "support", label: "Support", href: "/support", icon: "help", group: "security" },
  // Admin (Developer last)
  { id: "settings", label: "Settings", href: "/settings", icon: "settings", group: "admin" },
  { id: "dashboard", label: "Dashboard", href: "/dashboard", icon: "monitoring", group: "admin" },
  { id: "admin", label: "Admin", href: "/dashboard", icon: "shield", group: "admin" },
  { id: "users", label: "Users", href: "/settings/users", icon: "users", group: "admin" },
  { id: "tenants", label: "Tenants", href: "/tenants", icon: "users", group: "admin" },
  { id: "billing", label: "Billing", href: "/settings/billing", icon: "payments", group: "admin" },
  { id: "modules", label: "Modules", href: "/settings/modules", icon: "apps", group: "admin" },
  { id: "upgrade", label: "Keprix upgrades", href: "/settings/upgrade", icon: "backup", group: "admin" },
  { id: "feature-flags", label: "Feature Flags", href: "/admin/feature-flags", icon: "apps", group: "admin" },
  { id: "admin-quotas", label: "Quotas", href: "/admin/quotas", icon: "monitoring", group: "admin" },
  { id: "admin-tool-acl", label: "Tool ACL", href: "/admin/tools", icon: "shield", group: "admin" },
  { id: "admin-network-egress", label: "Network egress", href: "/admin/network-egress", icon: "shield", group: "admin" },
  { id: "admin-isolation-audit", label: "Isolation audit", href: "/admin/isolation-audit", icon: "shield", group: "admin" },
  { id: "admin-upstream", label: "Hermes upstream", href: "/admin/upstream", icon: "monitoring", group: "admin" },
  { id: "backup", label: "Backup", href: "/admin/backup", icon: "backup", group: "admin" },
  { id: "readiness", label: "Readiness", href: "/admin/readiness", icon: "monitoring", group: "admin" },
  { id: "self-knowledge", label: "Self-Knowledge", href: "/admin/self-knowledge", icon: "apps", group: "admin" },
  { id: "module-inventory", label: "Module inventory", href: "/developer/module-inventory", icon: "monitoring", group: "admin" },
  { id: "developer", label: "Developer", href: "/developer", icon: "code", group: "admin" },
];

export const mobilePrimaryNavigation: NavItem[] = primaryNavigation.filter((item) =>
  ["home", "chat", "brain", "tasks", "files", "settings"].includes(item.id),
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
  { id: "files", title: "Files", description: "Browse and preview the web vault.", href: "/files", icon: "folder" },
  { id: "notes", title: "Notes", description: "Capture linked notes and references.", href: "/notes", icon: "notes" },
  { id: "tasks", title: "Tasks", description: "Track work items and follow-ups.", href: "/tasks", icon: "tasks" },
  { id: "calendar", title: "Calendar", description: "Review schedules and deadlines.", href: "/calendar", icon: "calendar" },
  { id: "email", title: "Email", description: "Triage inbox threads with AI summaries.", href: "/email", icon: "email" },
  { id: "contacts", title: "Contacts", description: "Search people and sync address books.", href: "/contacts", icon: "contacts" },
  { id: "playbook", title: "Playbook", description: "Scan hardware and manage local models.", href: "/data?tab=models", icon: "playbook" },
  { id: "analytics", title: "Analytics", description: "Run verified Python analytics in an isolated session.", href: "/data?tab=analytics", icon: "compare" },
  { id: "compare", title: "Compare Models", description: "Blind A/B model evaluation.", href: "/compare", icon: "compare" },
  { id: "usage", title: "LLM usage", description: "Monitor token consumption and estimated spend.", href: "/data?tab=usage", icon: "monitoring" },
  { id: "video-ingest", title: "Video ingest", description: "Create transcript and frame manifests from local or remote videos.", href: "/data?tab=video", icon: "image" },
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

  // Prefer backend contract order (source of truth); fill gaps from the static fallback.
  const primaryById = new Map(primaryNavigation.map((item) => [item.id, item]));
  const items: NavItem[] = [];
  const seen = new Set<string>();
  for (const item of contract.navigation.items) {
    const fallback = primaryById.get(item.id);
    items.push({
      id: item.id,
      label: item.label,
      href: item.href,
      icon: item.icon || fallback?.icon || "apps",
      group: item.group as NavGroupId,
    });
    seen.add(item.id);
  }
  for (const item of primaryNavigation) {
    if (!seen.has(item.id)) {
      items.push(item);
    }
  }

  const groupIds = Array.from(
    new Set([
      ...contract.navigation.groups.map((group) => group.id as NavGroupId),
      ...items.map((item) => item.group),
    ]),
  );
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

/** Best-effort label for the current pathname from static nav (longest href match wins). */
export function labelForPath(pathname: string, items: NavItem[] = primaryNavigation): string {
  const path = pathname.split("?")[0] || "/";
  const ranked = [...items]
    .filter((item) => path === item.href || path.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length);
  if (ranked[0]) return ranked[0].label;
  if (path === "/" || path === "") return "Home";
  const segment = path.split("/").filter(Boolean).pop() || path;
  return segment.replace(/-/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
}
