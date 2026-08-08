"use client";

import Box from "@mui/material/Box";
import type { ReactNode } from "react";
import PageHeader from "@/components/ui/PageHeader";
import CrmTabNav from "@/components/crm/CrmTabNav";

export default function CrmLayout({ children }: { children: ReactNode }) {
  return (
    <Box>
      <PageHeader
        title="CRM"
        description="Workspace CRM for accounts, leads, contacts, deals, and lists. Soft Wall gates paying stages and enroll."
      />
      <CrmTabNav />
      <Box sx={{ mt: 3 }}>{children}</Box>
    </Box>
  );
}
