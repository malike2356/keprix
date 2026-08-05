"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function AdminReadinessPage() {
  return (
    <Box>
      <PageHeader
        title="Readiness"
        description="Deployment readiness checks for this workspace."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Readiness" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Readiness checks are still available through the admin API.
      </Alert>
      <Button component={Link} href="/control-center" variant="outlined">
        Back to admin
      </Button>
    </Box>
  );
}
