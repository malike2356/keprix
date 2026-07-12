export type SettingsNavItem = {
  label: string;
  href: string;
  icon: string;
  adminOnly?: boolean;
};

export const settingsNavigation: SettingsNavItem[] = [
  { label: "Overview", href: "/settings", icon: "settings" },
  { label: "Account", href: "/settings/account", icon: "users" },
  { label: "Modules", href: "/settings/modules", icon: "apps" },
  { label: "Messaging", href: "/settings/messaging", icon: "email" },
  { label: "Notifications", href: "/settings/notifications", icon: "settings" },
  { label: "Billing", href: "/settings/billing", icon: "payments" },
  { label: "Voice", href: "/settings/voice", icon: "voice" },
  { label: "Browser", href: "/settings/browser", icon: "extension" },
  { label: "Governance", href: "/settings/governance", icon: "shield" },
  { label: "Web search", href: "/settings/web-search", icon: "science", adminOnly: true },
  { label: "Users", href: "/settings/users", icon: "users", adminOnly: true },
  { label: "Upgrades", href: "/settings/upgrade", icon: "backup", adminOnly: true },
];

export function visibleSettingsNavigation(isAdmin: boolean): SettingsNavItem[] {
  return settingsNavigation.filter((item) => !item.adminOnly || isAdmin);
}

export function resolveSettingsNavValue(pathname: string, items: SettingsNavItem[]): string {
  const exact = items.find((item) => pathname === item.href);
  if (exact) return exact.href;

  const nested = items
    .filter((item) => item.href !== "/settings" && pathname.startsWith(`${item.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0];
  return nested?.href ?? "/settings";
}
