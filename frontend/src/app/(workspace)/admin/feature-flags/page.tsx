"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function AdminFeatureFlagsPage() {
  return (
    <Box>
      <PageHeader
        title="Feature flags"
        description="Runtime feature flag overrides for this workspace."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Feature flags" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Feature flag reads and overrides are still available through the
        admin API.
      </Alert>
      <Button component={Link} href="/control-center" variant="outlined">
        Back to admin
      </Button>
    </Box>
  );
}
