"use client";

import Box from "@mui/material/Box";
import AgentAppHub from "@/components/agent-apps/AgentAppHub";
import PageHeader from "@/components/ui/PageHeader";

export default function AgentAppsPage() {
  return (
    <Box>
      <PageHeader
        title="Agent apps"
        description="Install ready-made workflows or ship your own apps."
      />
      <AgentAppHub />
    </Box>
  );
}
