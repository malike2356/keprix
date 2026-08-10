import type { TablerIcon } from "@tabler/icons-react";
import {
  IconBrandTelegram,
  IconChartBar,
  IconCpu,
  IconCreditCard,
  IconDatabase,
  IconGitBranch,
  IconKey,
  IconLayoutDashboard,
  IconMessages,
  IconPlayerPlay,
  IconSettings,
  IconTools,
  IconUsers,
} from "@tabler/icons-react";

export type AdminNavEntry =
  | { type: "subheader"; title: string }
  | {
      type: "item";
      title: string;
      href: string;
      icon: TablerIcon;
      badgeKey?: "pendingMutations";
    };

export const ADMIN_NAV_ITEMS: AdminNavEntry[] = [
  { type: "item", title: "Admin overview", href: "/admin/dashboard", icon: IconLayoutDashboard },
  { type: "subheader", title: "Agent" },
  { type: "item", title: "Conversations", href: "/admin/conversations", icon: IconMessages },
  { type: "item", title: "Usage", href: "/admin/usage", icon: IconChartBar },
  { type: "item", title: "Models", href: "/admin/models", icon: IconCpu },
  { type: "item", title: "Tool Library", href: "/admin/tools", icon: IconTools },
  {
    type: "item",
    title: "Mutations",
    href: "/admin/mutations",
    icon: IconGitBranch,
    badgeKey: "pendingMutations",
  },
  { type: "item", title: "Memory Store", href: "/admin/memory", icon: IconDatabase },
  { type: "subheader", title: "Instance" },
  { type: "item", title: "Channels", href: "/dashboard/channels", icon: IconBrandTelegram },
  { type: "item", title: "API Keys", href: "/admin/keys", icon: IconKey },
  { type: "item", title: "Users", href: "/admin/users", icon: IconUsers },
  { type: "item", title: "Billing", href: "/admin/billing", icon: IconCreditCard },
  { type: "item", title: "Hermes upstream", href: "/admin/upstream", icon: IconGitBranch },
  { type: "item", title: "Settings", href: "/admin/settings", icon: IconSettings },
  { type: "item", title: "Engine control", href: "/admin/engine", icon: IconPlayerPlay },
];

export const ADMIN_SIDEBAR_WIDTH = 260;
export const ADMIN_SIDEBAR_COLLAPSED_WIDTH = 72;
export const ADMIN_SIDEBAR_COLLAPSED_KEY = "keprix_admin_sidebar_collapsed";
