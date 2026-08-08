"use client";

import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import PageHeader from "@/components/ui/PageHeader";
import OutreachTabNav from "@/components/outreach/OutreachTabNav";

export default function OutreachLayout({ children }: { children: ReactNode }) {
  return (
    <Box>
      <PageHeader
        title="Sales engagement"
        description="Lead intake, campaigns, Soft Wall sequences, and delivery channels. No mass-send without approval."
      />
      <OutreachTabNav />
      <Box sx={{ mt: 3 }}>{children}</Box>
    </Box>
  );
}
