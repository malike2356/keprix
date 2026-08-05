"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function AdminQuotasPage() {
  return (
    <Box>
      <PageHeader
        title="Quotas"
        description="Per-workspace usage quotas and rate limits."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Quotas" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Quota enforcement is still active on the backend.
      </Alert>
      <Button component={Link} href="/control-center" variant="outlined">
        Back to admin
      </Button>
    </Box>
  );
}
