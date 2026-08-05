"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";

export default function AccountSessionsPage() {
  return (
    <Box>
      <PageHeader
        title="Sessions"
        description="Devices and browsers currently signed in to your account."
      />
      <Alert severity="info" sx={{ mb: 2 }}>
        This page is being rebuilt. Sign out from other devices by resetting your password if you
        suspect unauthorized access.
      </Alert>
      <Button component={Link} href="/settings/account" variant="outlined">
        Back to account
      </Button>
    </Box>
  );
}
