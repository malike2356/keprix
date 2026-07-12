"use client";

import AgentOsSubnav from "@/components/agent-os/AgentOsSubnav";
import Box from "@mui/material/Box";

export default function AgentOsLayout({ children }: { children: React.ReactNode }) {
  return (
    <Box>
      <AgentOsSubnav />
      {children}
    </Box>
  );
}
