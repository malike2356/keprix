"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function IntegrationsPage() {
  return (
    <Box>
      <PageHeader
        title="Integrations"
        description="Connect third-party services and tools to your Keprix workspace."
        breadcrumbs={[{ label: "Settings", href: "/settings" }, { label: "Integrations" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Connectors can still be attached from the Playbook Studio node
        inspector in the meantime.
      </Alert>
      <Button component={Link} href="/settings" variant="outlined">
        Back to settings
      </Button>
    </Box>
  );
}
