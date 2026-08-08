"use client";

import Box from "@mui/material/Box";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/crm", label: "Overview", id: "overview" },
  { href: "/crm/pipeline", label: "Pipeline", id: "pipeline" },
  { href: "/crm/leads", label: "Leads", id: "leads" },
  { href: "/crm/contacts", label: "Contacts", id: "contacts" },
  { href: "/crm/accounts", label: "Accounts", id: "accounts" },
  { href: "/crm/deals", label: "Deals", id: "deals" },
  { href: "/crm/lists", label: "Lists", id: "lists" },
  { href: "/crm/icp", label: "ICP", id: "icp" },
  { href: "/crm/sla", label: "SLA", id: "sla" },
  { href: "/crm/integrations", label: "Integrations", id: "integrations" },
  { href: "/crm/experiments", label: "Experiments", id: "experiments" },
  { href: "/crm/data-quality", label: "Data quality", id: "data-quality" },
  { href: "/crm/enrich", label: "Enrich", id: "enrich" },
  { href: "/crm/discover", label: "Discover", id: "discover" },
  { href: "/crm/jobs", label: "Jobs", id: "jobs" },
  { href: "/crm/inbox", label: "Inbox", id: "inbox" },
  { href: "/crm/workflows", label: "Workflows", id: "workflows" },
  { href: "/crm/analytics", label: "Analytics", id: "analytics" },
  { href: "/crm/attribution", label: "Attribution", id: "attribution" },
  { href: "/crm/messaging", label: "Messaging", id: "messaging" },
  { href: "/crm/ops", label: "Ops", id: "ops" },
  { href: "/crm/deliverability", label: "Deliverability", id: "deliverability" },
  { href: "/crm/outbox", label: "Outbox", id: "outbox" },
  { href: "/crm/suppressions", label: "Suppressions", id: "suppressions" },
  { href: "/crm/contactability", label: "Contactability", id: "contactability" },
  { href: "/crm/merges", label: "Merges", id: "merges" },
  { href: "/crm/settings", label: "Settings", id: "settings" },
] as const;

function activeTabId(pathname: string): string {
  if (pathname === "/crm" || pathname === "/crm/") return "overview";
  for (const tab of TABS) {
    if (tab.id === "overview") continue;
    if (pathname === tab.href || pathname.startsWith(`${tab.href}/`)) return tab.id;
  }
  return "overview";
}

export function CrmTabNav() {
  const pathname = usePathname() || "/crm";
  const value = activeTabId(pathname);

  return (
    <Box
      component="nav"
      aria-label="CRM sections"
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        mt: 1,
        mb: 0,
        pb: 0.25,
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "stretch",
          gap: 0.25,
          rowGap: 0,
          width: "100%",
          maxWidth: "100%",
          overflowX: "hidden",
        }}
      >
        {TABS.map((tab) => {
          const selected = tab.id === value;
          return (
            <Box
              key={tab.id}
              component="a"
              href={tab.href}
              aria-current={selected ? "page" : undefined}
              sx={{
                display: "inline-flex",
                alignItems: "center",
                minHeight: 36,
                px: 1.25,
                py: 0.5,
                textDecoration: "none",
                fontWeight: selected ? 600 : 500,
                fontSize: "0.8125rem",
                lineHeight: 1.25,
                color: selected ? "text.primary" : "text.secondary",
                borderBottom: 2,
                borderColor: selected ? "primary.main" : "transparent",
                whiteSpace: "nowrap",
                flex: "0 0 auto",
                "&:hover": {
                  bgcolor: "action.hover",
                  borderColor: selected ? "primary.main" : "divider",
                  color: "text.primary",
                },
              }}
            >
              {tab.label}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

export default CrmTabNav;
