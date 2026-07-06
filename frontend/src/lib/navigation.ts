import type { UiContract, UiNavItem } from "@/lib/ui-contract";

export type NavGroupId =
  | "workspace"
  | "apps"
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
  "data",
  "research",
  "automations",
  "commerce",
  "security",
  "admin",
];

/** Static fallback aligned with backend ui_contract.navigation.NAV_ITEMS */
export const primaryNavigation: NavItem[] = [
  { id: "launcher", label: "Home", href: "/launcher", icon: "hub", group: "workspace" },
  { id: "chat", label: "Chat", href: "/chat", icon: "chat", group: "workspace" },
  { id: "documents", label: "Documents", href: "/documents", icon: "folder", group: "workspace" },
  { id: "notes", label: "Notes", href: "/notes", icon: "notes", group: "workspace" },
  { id: "tasks", label: "Tasks", href: "/tasks", icon: "tasks", group: "workspace" },
  { id: "calendar", label: "Calendar", href: "/calendar", icon: "calendar", group: "workspace" },
  { id: "email", label: "Email", href: "/email", icon: "email", group: "workspace" },
  { id: "contacts", label: "Contacts", href: "/contacts", icon: "contacts", group: "workspace" },
  { id: "gallery", label: "Gallery", href: "/gallery", icon: "image", group: "workspace" },
  { id: "memory", label: "Memory", href: "/memory", icon: "memory", group: "workspace" },
  { id: "skills", label: "Skills Hub", href: "/skills", icon: "skills", group: "apps" },
  { id: "hub", label: "Hub", href: "/hub", icon: "apps", group: "apps" },
  { id: "builder", label: "Project Builder", href: "/builder", icon: "code", group: "apps" },
  { id: "domain-packs", label: "Domain Packs", href: "/domain-packs", icon: "skills", group: "apps" },
  { id: "migrate", label: "Migrate", href: "/migrate", icon: "backup", group: "apps" },
  { id: "messaging-settings", label: "Messaging", href: "/settings/messaging", icon: "email", group: "apps" },
  { id: "voice-wake", label: "Wake words", href: "/settings/voice/wake-words", icon: "settings", group: "apps" },
  { id: "opportunities", label: "Opportunities", href: "/opportunities", icon: "science", group: "research" },
  { id: "research", label: "Deep Research", href: "/research", icon: "science", group: "research" },
  { id: "compare", label: "Compare Models", href: "/compare", icon: "compare", group: "research" },
  { id: "playbook", label: "Local models", href: "/playbook", icon: "playbook", group: "data" },
  { id: "playbooks", label: "Playbooks", href: "/playbooks", icon: "playbook", group: "automations" },
  { id: "agent-teams", label: "Agent Teams", href: "/admin/teams", icon: "extension", group: "automations" },
  { id: "agent-runtime", label: "Agent Runtime", href: "/agent-runtime", icon: "extension", group: "automations" },
  { id: "browser-adoption", label: "Browser", href: "/browser", icon: "extension", group: "automations" },
  { id: "analytics-adoption", label: "Analytics", href: "/analytics", icon: "compare", group: "automations" },
  { id: "coding-adoption", label: "Coding", href: "/admin/coding", icon: "code", group: "automations" },
  { id: "tools-adoption", label: "Tools", href: "/admin/tools", icon: "extension", group: "automations" },
  { id: "evals", label: "Evals", href: "/evals", icon: "science", group: "automations" },
  { id: "control-center", label: "Control Center", href: "/control-center", icon: "hub", group: "automations" },
  { id: "agent-studio", label: "Agent Studio", href: "/agent-studio", icon: "apps", group: "automations" },
  { id: "agent-apps", label: "Agent Apps", href: "/agent-apps", icon: "apps", group: "automations" },
  { id: "rag-pipeline", label: "RAG Pipelines", href: "/rag-pipeline", icon: "science", group: "data" },
  { id: "analytics", label: "Analytics", href: "/analytics", icon: "compare", group: "data" },
  { id: "usage", label: "LLM usage", href: "/usage", icon: "monitoring", group: "data" },
  { id: "review-gateway", label: "Review gateway", href: "/review-gateway", icon: "shield", group: "security" },
  { id: "vault", label: "Vault", href: "/vault", icon: "lock", group: "security" },
  { id: "support", label: "Support", href: "/support", icon: "help", group: "security" },
  { id: "cron", label: "Cron Jobs", href: "/admin/cron", icon: "schedule", group: "automations" },
  { id: "mcp", label: "MCP Servers", href: "/admin/mcp", icon: "extension", group: "automations" },
  { id: "backup", label: "Backup", href: "/admin/backup", icon: "backup", group: "admin" },
  { id: "users", label: "Users", href: "/settings/users", icon: "users", group: "admin" },
  { id: "billing", label: "Billing", href: "/settings/billing", icon: "payments", group: "admin" },
  { id: "settings", label: "Settings", href: "/settings", icon: "settings", group: "admin" },
  { id: "developer", label: "Developer", href: "/developer", icon: "code", group: "admin" },
];

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
  { id: "gallery", title: "Gallery", description: "Review generated and uploaded images.", href: "/gallery", icon: "image" },
  { id: "vault", title: "Vault", description: "Manage encrypted credentials.", href: "/vault", icon: "lock" },
  { id: "cron", title: "Cron Jobs", description: "Schedule recurring agent tasks.", href: "/admin/cron", icon: "schedule" },
  { id: "mcp", title: "MCP Servers", description: "Connect external tool servers.", href: "/admin/mcp", icon: "extension" },
  { id: "agent-apps", title: "Agent Apps", description: "Install ready-made workflows or ship your own apps.", href: "/agent-apps", icon: "apps" },
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

  return {
    groups: groupIds.map((id) => ({
      id,
      label: contract.navigation.groups.find((group) => group.id === id)?.label || navGroupLabels[id],
    })),
    items,
  };
}
