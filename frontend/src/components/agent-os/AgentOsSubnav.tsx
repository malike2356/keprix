"use client";

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Stack from "@mui/material/Stack";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { id: "glass", label: "Glass", href: "/agent-os/glass" },
  { id: "board", label: "Board", href: "/agent-os" },
  { id: "onboarding", label: "Onboarding", href: "/agent-os/onboarding" },
  { id: "memory", label: "Memory", href: "/memory/galaxy" },
  { id: "usage", label: "Usage", href: "/usage" },
] as const;

function activeId(pathname: string): string {
  if (pathname.startsWith("/agent-os/glass")) return "glass";
  if (pathname === "/agent-os" || pathname.startsWith("/agent-os/runs")) return "board";
  if (pathname.startsWith("/agent-os/onboarding") || pathname.startsWith("/agent-os/onboard")) {
    return "onboarding";
  }
  if (pathname.startsWith("/memory") || pathname.startsWith("/brain")) return "memory";
  if (pathname.startsWith("/usage")) return "usage";
  if (pathname.startsWith("/agent-os")) return "board";
  return "glass";
}

export default function AgentOsSubnav() {
  const pathname = usePathname() || "/agent-os/glass";
  const value = activeId(pathname);

  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={1}
      sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
    >
      <Tabs value={value} sx={{ minHeight: 44 }} variant="scrollable" allowScrollButtonsMobile>
        {ITEMS.map((item) => (
          <Tab
            key={item.id}
            label={item.label}
            value={item.id}
            component={Link}
            href={item.href}
            sx={{ minHeight: 44 }}
          />
        ))}
      </Tabs>
    </Stack>
  );
}

export const AGENT_OS_HUB_HOME = "/agent-os/glass";

export const AGENT_OS_MORE_LINKS = [
  { label: "Self-improvement settings", href: "/settings/agent/self-improvement" },
  { label: "Activation checklist", href: "/agent-os/onboarding" },
  { label: "Onboard interview", href: "/agent-os/onboard" },
  { label: "Workflow audit", href: "/agent-os/audit" },
  { label: "OS maturity", href: "/agent-os/maturity" },
  { label: "Connections", href: "/agent-os/connections" },
  { label: "Skill proposals", href: "/agent-os/skill-proposals" },
  { label: "Improvement proposals", href: "/agent-os/improvements" },
  { label: "Skill review", href: "/agent-os/skill-review" },
  { label: "Promote skill", href: "/agent-os/promote" },
  { label: "Run ledger", href: "/agent-os/runs" },
  { label: "Loop profiles", href: "/agent-os/loop-profiles" },
  { label: "Client kit", href: "/settings/agent-os/client-kit" },
] as const;
