"use client";

import Box from "@mui/material/Box";
import BrowserProfileSettings from "@/components/browser/BrowserProfileSettings";
import BrowserSessionPanel from "@/components/browser/BrowserSessionPanel";
import PageHeader from "@/components/ui/PageHeader";

export default function BrowserSettingsPage() {
  return (
    <Box>
      <PageHeader
        title="Browser harness"
        description="Agent browser sessions, encrypted profiles, and governed automation skills."
      />
      <Box sx={{ display: "grid", gap: 2 }}>
        <BrowserSessionPanel />
        <BrowserProfileSettings />
      </Box>
    </Box>
  );
}
