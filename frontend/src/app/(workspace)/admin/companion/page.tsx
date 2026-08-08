"use client";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import * as React from "react";
import useSWR from "swr";
import EmptyState from "@/components/ui/EmptyState";
import PageHeader from "@/components/ui/PageHeader";
import { SkeletonList, SkeletonTable } from "@/components/ui/loading";
import { useCESession } from "@/lib/ce-auth";
import {
  createCompanionPairing,
  fetchCompanionDevices,
  revokeCompanionDevice,
  type CompanionDevice,
  type CompanionPairingSession,
} from "@/lib/companion-api";

function isAdminRole(role: string | undefined): boolean {
  const r = (role || "").toLowerCase();
  return r === "admin" || r === "owner" || r === "superadmin" || r === "developer";
}

export default function CompanionAdminPage() {
  const { user, isLoading: sessionLoading } = useCESession();
  const isAdmin = isAdminRole(user?.role);
  const [message, setMessage] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [serverUrl, setServerUrl] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [session, setSession] = React.useState<CompanionPairingSession | null>(null);
  const [revokeTarget, setRevokeTarget] = React.useState<CompanionDevice | null>(null);

  const devices = useSWR(isAdmin ? "companion-devices" : null, () => fetchCompanionDevices());

  if (sessionLoading) {
    return (
      <Box>
        <PageHeader title="Companion pairing" description="Pair mobile companions with QR or short code." />
        <SkeletonList rows={4} rowHeight={48} />
      </Box>
    );
  }

  if (!isAdmin) {
    return (
      <Box>
        <PageHeader title="Companion pairing" description="Pair mobile companions with QR or short code." />
        <Alert severity="error">Admin role required to pair or revoke companion devices.</Alert>
      </Box>
    );
  }

  async function onCreatePair() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const next = await createCompanionPairing({
        serverUrl: serverUrl.trim() || undefined,
      });
      setSession(next);
      setMessage("Pairing session created. Scan the QR or enter the short code on the device.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pairing failed");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmRevoke() {
    if (!revokeTarget) return;
    const id = String(revokeTarget.device_id || "");
    if (!id) return;
    setBusy(true);
    setError(null);
    try {
      await revokeCompanionDevice(id);
      setMessage(`Revoked device ${revokeTarget.device_name || revokeTarget.name || id}.`);
      setRevokeTarget(null);
      await devices.mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoke failed");
    } finally {
      setBusy(false);
    }
  }

  const rows = devices.data?.devices ?? [];

  return (
    <Box>
      <PageHeader
        title="Companion pairing"
        description="Create a QR pairing session for mobile companions. Device tokens are issued only at confirm time and are never shown again here."
        breadcrumbs={[{ label: "Admin", href: "/control-center" }, { label: "Companion" }]}
      />

      {error ? (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      ) : null}
      {message ? (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      ) : null}

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          New pairing session
        </Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="flex-start">
          <TextField
            size="small"
            label="Server URL (optional)"
            value={serverUrl}
            onChange={(e) => setServerUrl(e.target.value)}
            placeholder="https://keprix.example.com"
            sx={{ flex: 1, minWidth: 240 }}
            helperText="Defaults to LAN candidate if blank."
          />
          <Button variant="contained" disabled={busy} onClick={() => void onCreatePair()}>
            Create pair session
          </Button>
        </Stack>

        {session ? (
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mt: 2 }} alignItems="flex-start">
            {session.qr ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={session.qr}
                alt="Companion pairing QR"
                width={180}
                height={180}
                style={{ borderRadius: 8, background: "#fff" }}
              />
            ) : null}
            <Box>
              <Typography variant="body2">Short code</Typography>
              <Typography variant="h4" sx={{ letterSpacing: 4, fontFamily: "monospace" }}>
                {session.code}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Expires: {session.expires_at}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Pairing id: {session.pairing_id}
              </Typography>
            </Box>
          </Stack>
        ) : null}
      </Paper>

      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Paired devices
      </Typography>
      {devices.isLoading ? (
        <SkeletonTable rows={3} columns={4} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No paired devices"
          description="Create a pairing session, then confirm from the mobile companion app."
        />
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Platform</TableCell>
              <TableCell>Last seen</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={String(row.device_id)}>
                <TableCell>{row.device_name || row.name || row.device_id}</TableCell>
                <TableCell>{row.platform || "-"}</TableCell>
                <TableCell>{String(row.last_seen_at || row.paired_at || "-")}</TableCell>
                <TableCell align="right">
                  <Button size="small" color="error" disabled={busy} onClick={() => setRevokeTarget(row)}>
                    Revoke
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={Boolean(revokeTarget)} onClose={() => setRevokeTarget(null)}>
        <DialogTitle>Revoke companion device?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Soft Wall confirm: revoke{" "}
            {revokeTarget?.device_name || revokeTarget?.name || revokeTarget?.device_id}. The device
            API key stops working immediately.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevokeTarget(null)}>Cancel</Button>
          <Button color="error" variant="contained" disabled={busy} onClick={() => void onConfirmRevoke()}>
            Revoke
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
