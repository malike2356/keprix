"use client";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { IconUsers } from "@tabler/icons-react";
import * as React from "react";
import useSWR from "swr";
import DashboardCard from "@/components/cards/DashboardCard";
import EmptyState from "@/components/ui/EmptyState";
import { SkeletonTable } from "@/components/ui/loading";
import {
  deleteWorkspaceUser,
  fetchWorkspaceUsers,
  inviteWorkspaceUser,
  resendWorkspaceInvite,
  resetWorkspaceUserTotp,
  revokeWorkspaceInvite,
  updateWorkspaceUser,
  type WorkspaceUser,
} from "@/lib/admin-workspace-api";
import { formatTimeAgo } from "@/lib/time-ago";

function roleLabel(role: string): string {
  if (role === "owner") return "Owner";
  if (role === "admin") return "Admin";
  return "User";
}

function roleChipColor(role: string): "primary" | "secondary" | "default" {
  if (role === "owner") return "primary";
  if (role === "admin") return "secondary";
  return "default";
}

export default function WorkspaceUsersManager() {
  const { data, isLoading, mutate } = useSWR("workspace-users", fetchWorkspaceUsers);
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [manageTarget, setManageTarget] = React.useState<WorkspaceUser | null>(null);
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState("user");
  const [message, setMessage] = React.useState("");
  const [editRole, setEditRole] = React.useState("user");
  const [editStatus, setEditStatus] = React.useState<"active" | "invited" | "suspended">("active");
  const [actionError, setActionError] = React.useState<string | null>(null);
  const [inviteLink, setInviteLink] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const users = data?.items || [];

  const openManage = (user: WorkspaceUser) => {
    setManageTarget(user);
    setEditRole(user.role === "admin" ? "admin" : "user");
    setEditStatus(user.status);
    setActionError(null);
    setInviteLink(null);
  };

  const closeManage = () => {
    setManageTarget(null);
    setActionError(null);
    setInviteLink(null);
  };

  const handleInvite = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const result = await inviteWorkspaceUser({ email: email.trim(), role, message: message.trim() || undefined });
      if (!result.email_sent) {
        setInviteLink(result.invite_url);
      } else {
        setInviteOpen(false);
        setEmail("");
        setMessage("");
      }
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Invite failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSaveUser = async () => {
    if (!manageTarget || manageTarget.source === "invite" || manageTarget.role === "owner") return;
    setBusy(true);
    setActionError(null);
    try {
      await updateWorkspaceUser(manageTarget.id, { role: editRole, status: editStatus });
      await mutate();
      closeManage();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!manageTarget || manageTarget.source === "invite" || manageTarget.role === "owner") return;
    setBusy(true);
    setActionError(null);
    try {
      await deleteWorkspaceUser(manageTarget.id);
      await mutate();
      closeManage();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  };

  const handleResendInvite = async () => {
    if (!manageTarget?.invite_id) return;
    setBusy(true);
    setActionError(null);
    try {
      const result = await resendWorkspaceInvite(manageTarget.invite_id);
      if (!result.email_sent) {
        setInviteLink(result.invite_url);
      }
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Resend failed");
    } finally {
      setBusy(false);
    }
  };

  const handleRevokeInvite = async () => {
    if (!manageTarget?.invite_id) return;
    setBusy(true);
    setActionError(null);
    try {
      await revokeWorkspaceInvite(manageTarget.invite_id);
      await mutate();
      closeManage();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  };

  const handleResetTotp = async () => {
    if (!manageTarget || manageTarget.source === "invite") return;
    setBusy(true);
    setActionError(null);
    try {
      await resetWorkspaceUserTotp(manageTarget.id);
      await mutate();
      closeManage();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "2FA reset failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 4 }}>
          <DashboardCard title="Total users" middleContent={<Typography variant="h4">{data?.stats.total ?? 0}</Typography>} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <DashboardCard title="Active" middleContent={<Typography variant="h4">{data?.stats.active ?? 0}</Typography>} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <DashboardCard title="Pending invites" middleContent={<Typography variant="h4">{data?.stats.pending_invites ?? 0}</Typography>} />
        </Grid>
      </Grid>

      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 2 }}>
        <Button
          variant="contained"
          onClick={() => {
            setInviteOpen(true);
            setInviteLink(null);
            setActionError(null);
          }}
        >
          Invite user
        </Button>
      </Box>

      {isLoading ? (
        <SkeletonTable rows={6} columns={6} />
      ) : !users.length ? (
        <EmptyState
          title="No users yet"
          description="Invite teammates to access this Keprix workspace."
          icon={<IconUsers size={48} stroke={1.5} />}
        />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name + email</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Joined</TableCell>
              <TableCell>Last active</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map((user) => (
              <TableRow key={`${user.source || "account"}-${user.id}`}>
                <TableCell>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Avatar sx={{ width: 28, height: 28, fontSize: 12 }}>
                      {(user.name || "U").slice(0, 1).toUpperCase()}
                    </Avatar>
                    <Box>
                      <Typography variant="body2">{user.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {user.email}
                      </Typography>
                    </Box>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip size="small" color={roleChipColor(user.role)} label={roleLabel(user.role)} />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                    <Chip
                      size="small"
                      color={user.status === "active" ? "success" : user.status === "invited" ? "warning" : "default"}
                      label={user.status}
                    />
                    {user.source !== "invite" && user.totp_enabled ? (
                      <Chip size="small" color="info" label="2FA" />
                    ) : null}
                  </Box>
                </TableCell>
                <TableCell>{user.joined_at ? formatTimeAgo(String(user.joined_at)) : "Invite pending"}</TableCell>
                <TableCell>{formatTimeAgo(user.last_active_at) || "Never"}</TableCell>
                <TableCell align="right">
                  <Button size="small" onClick={() => openManage(user)} disabled={user.role === "owner"}>
                    {user.role === "owner" ? "Owner" : "Manage"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={inviteOpen} onClose={() => setInviteOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Invite user</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          {actionError ? <Alert severity="error">{actionError}</Alert> : null}
          {inviteLink ? (
            <Alert severity="info">
              SMTP is not configured. Share this invite link manually:
              <Box component="code" sx={{ display: "block", mt: 1, wordBreak: "break-all" }}>
                {inviteLink}
              </Box>
            </Alert>
          ) : null}
          <TextField label="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
          <TextField select label="Role" value={role} onChange={(event) => setRole(event.target.value)}>
            <MenuItem value="user">User</MenuItem>
            <MenuItem value="admin">Admin</MenuItem>
          </TextField>
          <TextField
            label="Custom message (optional)"
            multiline
            minRows={3}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setInviteOpen(false)}>Close</Button>
          <Button variant="contained" disabled={!email.trim() || busy} onClick={() => void handleInvite()}>
            Send invite
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(manageTarget)} onClose={closeManage} maxWidth="sm" fullWidth>
        <DialogTitle>{manageTarget?.source === "invite" ? "Pending invite" : "Manage user"}</DialogTitle>
        <DialogContent sx={{ display: "grid", gap: 2, pt: 1 }}>
          {actionError ? <Alert severity="error">{actionError}</Alert> : null}
          {inviteLink ? (
            <Alert severity="info">
              Share this invite link:
              <Box component="code" sx={{ display: "block", mt: 1, wordBreak: "break-all" }}>
                {inviteLink}
              </Box>
            </Alert>
          ) : null}
          <DialogContentText>
            {manageTarget?.email}
            {manageTarget?.expires_at ? ` (expires ${manageTarget.expires_at})` : ""}
          </DialogContentText>
          {manageTarget?.source === "invite" ? null : (
            <>
              {manageTarget?.totp_enabled ? (
                <Alert severity="info">This user has two-factor authentication enabled.</Alert>
              ) : null}
              <TextField select label="Role" value={editRole} onChange={(event) => setEditRole(event.target.value)}>
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </TextField>
              <TextField
                select
                label="Status"
                value={editStatus}
                onChange={(event) => setEditStatus(event.target.value as typeof editStatus)}
              >
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="suspended">Suspended</MenuItem>
                <MenuItem value="invited">Invited (unapproved)</MenuItem>
              </TextField>
            </>
          )}
        </DialogContent>
        <DialogActions sx={{ justifyContent: "space-between", px: 3, pb: 2 }}>
          <Box>
            {manageTarget?.source === "invite" ? (
              <>
                <Button onClick={() => void handleResendInvite()} disabled={busy}>
                  Resend
                </Button>
                <Button color="error" onClick={() => void handleRevokeInvite()} disabled={busy}>
                  Revoke
                </Button>
              </>
            ) : (
              <>
                {manageTarget?.totp_enabled ? (
                  <Button color="warning" onClick={() => void handleResetTotp()} disabled={busy}>
                    Reset 2FA
                  </Button>
                ) : null}
                <Button color="error" onClick={() => void handleDeleteUser()} disabled={busy}>
                  Delete
                </Button>
              </>
            )}
          </Box>
          <Box>
            <Button onClick={closeManage}>Cancel</Button>
            {manageTarget?.source === "invite" ? null : (
              <Button variant="contained" onClick={() => void handleSaveUser()} disabled={busy}>
                Save
              </Button>
            )}
          </Box>
        </DialogActions>
      </Dialog>
    </>
  );
}
