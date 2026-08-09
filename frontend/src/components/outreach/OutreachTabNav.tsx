"use client";

import Box from "@mui/material/Box";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/outreach", label: "Overview", id: "overview" },
  { href: "/outreach/pipeline", label: "Pipeline", id: "pipeline" },
  { href: "/outreach/leads", label: "Leads", id: "leads" },
  { href: "/outreach/replies", label: "Replies", id: "replies" },
  { href: "/outreach/bookings", label: "Bookings", id: "bookings" },
  { href: "/outreach/lists", label: "Lists", id: "lists" },
  { href: "/outreach/campaigns", label: "Campaigns", id: "campaigns" },
  { href: "/outreach/sequences", label: "Sequences", id: "sequences" },
  { href: "/outreach/channels", label: "Channels", id: "channels" },
  { href: "/outreach/companies-house", label: "Companies House", id: "companies-house" },
  { href: "/outreach/approvals", label: "Approvals", id: "approvals" },
  { href: "/outreach/deliverability", label: "Deliverability", id: "deliverability" },
  { href: "/outreach/outbox", label: "Outbox", id: "outbox" },
  { href: "/outreach/suppressions", label: "Suppressions", id: "suppressions" },
  { href: "/outreach/contactability", label: "Contactability", id: "contactability" },
  { href: "/outreach/merges", label: "Merges", id: "merges" },
  { href: "/outreach/settings", label: "Safety", id: "settings" },
] as const;

function activeTabId(pathname: string): string {
  if (pathname === "/outreach" || pathname === "/outreach/") return "overview";
  for (const tab of TABS) {
    if (tab.id === "overview") continue;
    if (pathname === tab.href || pathname.startsWith(`${tab.href}/`)) return tab.id;
  }
  return "overview";
}

export function OutreachTabNav() {
  const pathname = usePathname() || "/outreach";
  const value = activeTabId(pathname);

  return (
    <Box
      component="nav"
      aria-label="Outreach sections"
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        mt: 1,
        mb: 0,
        pb: 0.25,
        width: "100%",
        minWidth: 0,
        maxWidth: "100%",
      }}
    >
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "stretch",
          columnGap: 0.25,
          rowGap: 0.25,
          width: "100%",
          minWidth: 0,
          maxWidth: "100%",
          overflowX: "hidden",
        }}
      >
        {TABS.map((tab) => {
          const selected = tab.id === value;
          // Use a real <a> (same as CrmTabNav). MUI Box + next/link often
          // fails to forward href / client-navigate in the workspace shell.
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
                cursor: "pointer",
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

export default OutreachTabNav;

