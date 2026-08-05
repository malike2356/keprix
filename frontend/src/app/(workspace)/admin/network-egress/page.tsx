"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function AdminNetworkEgressPage() {
  return (
    <Box>
      <PageHeader
        title="Network egress"
        description="Outbound network policy and allowlists for agent tool calls."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Network egress" }]}
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Egress policy is still enforced by the backend.
      </Alert>
      <Button component={Link} href="/control-center" variant="outlined">
        Back to admin
      </Button>
    </Box>
  );
}
