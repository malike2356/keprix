"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function SettingsUpgradePage() {
  return (
    <Box>
      <PageHeader
        title="Upgrade"
        description="Review available Keprix upgrades and notification preferences."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Upgrade" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Upgrade alerts still appear in the workspace banner when a new
        version is available.
      </Alert>
      <Button component={Link} href="/settings" variant="outlined">
        Back to settings
      </Button>
    </Box>
  );
}
