"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import NextLink from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonTable } from "@/components/ui/loading";
import WorkspaceUsersManager from "@/components/users/WorkspaceUsersManager";
import { useCESession } from "@/lib/ce-auth";

export default function SettingsUsersPage() {
  const { user, isLoading } = useCESession();
  const isAdmin = user?.role === "admin" || user?.role === "owner";

  if (isLoading) {
    return (
      <Box>
        <PageHeader title="Users" description="Invite teammates and manage workspace access." />
        <SkeletonTable rows={6} columns={6} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Users" description="Invite teammates and manage workspace access." />
        <Alert severity="warning" sx={{ mb: 2 }}>
          Only admins can manage workspace users. Ask an instance admin for access.
        </Alert>
        <Button component={NextLink} href="/settings" variant="outlined">
          Back to settings
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title="Users"
        description="Human accounts for this instance: invite, assign roles (owner, admin, user), suspend, or remove access."
      />
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Accounts are stored in the instance auth store. Pending invites send an email or shareable link to
        {" "}
        <code>/auth/accept-invite</code>. For multi-agent YAML crews (not people), open{" "}
        <Button component={NextLink} href="/admin/teams" size="small" sx={{ verticalAlign: "baseline", p: 0, minWidth: 0 }}>
          Agent teams
        </Button>
        .
      </Typography>
      <WorkspaceUsersManager />
    </Box>
  );
}
