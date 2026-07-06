"use client";

import * as React from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import DeleteIcon from "@mui/icons-material/Delete";
import useSWR from "swr";
import AdminTable from "@/components/admin/AdminTable";
import ConfirmDialog from "@/components/admin/ConfirmDialog";
import UserFormDialog from "@/components/admin/UserFormDialog";
import PageContainer from "@/components/shared/PageContainer";
import WorkspaceUsersManager from "@/components/users/WorkspaceUsersManager";
import { deleteAdminUser, fetchAdminUsers, type AdminUser } from "@/lib/admin-pages-api";
import { useRequireAdmin } from "@/lib/ce-auth";

export default function AdminUsersPage() {
  useRequireAdmin();
  const { data, isLoading, mutate } = useSWR("admin-users-table", fetchAdminUsers);
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [deleteTarget, setDeleteTarget] = React.useState<AdminUser | null>(null);

  const columns = [
    { id: "username", label: "Username" },
    { id: "email", label: "Email", render: (row: AdminUser) => row.email || "—" },
    {
      id: "role",
      label: "Role",
      render: (row: AdminUser) => (
        <Chip
          label={row.role}
          size="small"
          color={row.role === "admin" || row.role === "owner" ? "primary" : "default"}
          variant="outlined"
        />
      ),
    },
    {
      id: "created_at",
      label: "Created",
      render: (row: AdminUser) =>
        row.created_at ? new Date(row.created_at).toLocaleDateString() : "—",
    },
    {
      id: "actions",
      label: "",
      width: 60,
      render: (row: AdminUser) => (
        <IconButton size="small" onClick={(e) => { e.stopPropagation(); setDeleteTarget(row); }}>
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ];

  return (
    <PageContainer title="Users" description="Workspace access, invites, and team onboarding." padded={false}>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <AdminTable
          title="Instance users"
          columns={columns}
          rows={data ?? []}
          loading={isLoading}
          action={
            <Button size="small" variant="contained" onClick={() => setDialogOpen(true)}>
              Invite user
            </Button>
          }
        />
        <WorkspaceUsersManager />
      </Box>

      <UserFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSaved={() => { void mutate(); setDialogOpen(false); }}
      />
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete user"
        body={`Delete "${deleteTarget?.username}"? This cannot be undone.`}
        onConfirm={async () => {
          if (!deleteTarget) return;
          await deleteAdminUser(deleteTarget.id);
          void mutate();
          setDeleteTarget(null);
        }}
        onClose={() => setDeleteTarget(null)}
      />
    </PageContainer>
  );
}
