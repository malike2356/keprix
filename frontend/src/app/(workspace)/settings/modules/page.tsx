"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function SettingsModulesPage() {
  return (
    <Box>
      <PageHeader
        title="Modules"
        description="Enable or disable optional Keprix modules for this workspace."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Modules" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. A2A and Observability remain reachable directly while the module
        list is restored.
      </Alert>
      <Button component={Link} href="/settings" variant="outlined">
        Back to settings
      </Button>
    </Box>
  );
}
