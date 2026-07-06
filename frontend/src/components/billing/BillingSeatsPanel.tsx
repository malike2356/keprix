"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import DashboardCard from "@/components/cards/DashboardCard";
import { SkeletonList } from "@/components/ui/loading";
import type { BillingSeat } from "@/lib/billing-api";

type BillingSeatsPanelProps = {
  seats: BillingSeat[];
  seatsIncluded: number;
  loading?: boolean;
  actionLoading?: boolean;
  onInvite: (email: string, role: string) => Promise<void>;
  onRemove: (seatId: string) => Promise<void>;
};

export default function BillingSeatsPanel({
  seats,
  seatsIncluded,
  loading,
  actionLoading,
  onInvite,
  onRemove,
}: BillingSeatsPanelProps) {
  const [email, setEmail] = React.useState("");
  const [role, setRole] = React.useState("member");
  const [removeTarget, setRemoveTarget] = React.useState<BillingSeat | null>(null);

  const handleInvite = async () => {
    if (!email.trim()) return;
    await onInvite(email.trim(), role);
    setEmail("");
  };

  const handleConfirmRemove = async () => {
    if (!removeTarget) return;
    await onRemove(removeTarget.id);
    setRemoveTarget(null);
  };

  return (
    <DashboardCard
      title="Team seats"
      subtitle={`${seats.length} used / ${seatsIncluded} included`}
    >
      {loading ? (
        <SkeletonList rows={4} rowHeight={48} />
      ) : (
        <Stack spacing={2}>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", alignItems: "flex-start" }}>
            <TextField
              size="small"
              label="Email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              sx={{ minWidth: 220, flex: 1 }}
            />
            <TextField
              select
              size="small"
              label="Role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="member">Member</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </TextField>
            <Button variant="contained" onClick={handleInvite} disabled={actionLoading || !email.trim()}>
              Invite
            </Button>
          </Box>

          {seats.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No team members invited yet.
            </Typography>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Email</TableCell>
                    <TableCell>Role</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {seats.map((seat) => (
                    <TableRow key={seat.id}>
                      <TableCell>{seat.email}</TableCell>
                      <TableCell>{seat.role}</TableCell>
                      <TableCell>{seat.status || "active"}</TableCell>
                      <TableCell align="right">
                        <Button size="small" color="error" onClick={() => setRemoveTarget(seat)}>
                          Remove
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Stack>
      )}

      <Dialog open={Boolean(removeTarget)} onClose={() => setRemoveTarget(null)}>
        <DialogTitle>Remove seat?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Remove {removeTarget?.email} from your team? They will lose access when the seat is removed.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveTarget(null)}>Cancel</Button>
          <Button color="error" onClick={handleConfirmRemove} disabled={actionLoading}>
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </DashboardCard>
  );
}
