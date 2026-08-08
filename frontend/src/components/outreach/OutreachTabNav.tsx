"use client";

import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Link from "next/link";
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
    <Box sx={{ borderBottom: 1, borderColor: "divider", mt: 1, mb: 0 }}>
      <Tabs
        value={value}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{
          minHeight: 40,
          "& .MuiTab-root": {
            minHeight: 40,
            textTransform: "none",
            fontWeight: 500,
            color: "text.secondary",
            px: 1.5,
            py: 0,
          },
          "& .Mui-selected": {
            color: "text.primary",
            fontWeight: 600,
          },
          "& .MuiTabs-indicator": {
            height: 2,
            borderRadius: 1,
          },
        }}
      >
        {TABS.map((tab) => (
          <Tab
            key={tab.id}
            label={tab.label}
            value={tab.id}
            component={Link}
            href={tab.href}
          />
        ))}
      </Tabs>
    </Box>
  );
}

export default OutreachTabNav;
